/* eslint-disable @typescript-eslint/no-require-imports */
const assert = require('node:assert/strict');
const { after, before, test } = require('node:test');
const { execFile } = require('node:child_process');
const { copyFile, mkdir, mkdtemp, readFile, readdir, rm, writeFile } = require('node:fs/promises');
const { createServer } = require('node:http');
const { tmpdir } = require('node:os');
const { join } = require('node:path');
const { promisify } = require('node:util');
const { once } = require('node:events');
const { AudioConversionError, getAudioExtension, getDownloadFilename, prepareAudioFile } = require('../src/lib/audio.ts');
const { saveMusicToLibrary } = require('../src/lib/download.ts');
const { getProvider } = require('../src/lib/providers/index.ts');
const { GET, POST } = require('../src/app/api/download/route.ts');
const { NextRequest } = require('next/server');

const exec = promisify(execFile);
const musicItem = { id: 'test', title: '测试歌曲', artist: '测试歌手', album: '测试专辑', provider: 'gequbao' };
let root;
let server;
let baseUrl;
let originalGetPlayInfo;
let originalEnv;
const assets = {};

async function probe(path) {
  const { stdout } = await exec('ffprobe', ['-v', 'error', '-show_streams', '-show_format', '-of', 'json', path]);
  return JSON.parse(stdout);
}

function playInfo(name) {
  return { url: `${baseUrl}/${name}`, type: name.split('.').pop(), lyrics: '[00:00.00]测试歌词' };
}

async function browserDownload(name, enabled, filename = '测试歌手 - 测试歌曲.mp3') {
  const params = new URLSearchParams({ id: name, saveToNas: 'false', filename });
  if (enabled !== undefined) params.set('convertAacToMp3', String(enabled));
  return GET(new NextRequest(`http://localhost/api/download?${params}`));
}

before(async () => {
  root = await mkdtemp(join(tmpdir(), 'coco-audio-test-'));
  for (const [name, codec, format] of [
    ['source.aac', 'aac', 'adts'],
    ['source.m4a', 'aac', 'ipod'],
    ['source.mp3', 'libmp3lame', 'mp3'],
    ['source.flac', 'flac', 'flac'],
    ['alac.m4a', 'alac', 'ipod'],
  ]) {
    const path = join(root, name);
    await exec('ffmpeg', ['-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.15', '-c:a', codec, '-f', format, path]);
    assets[name] = await readFile(path);
  }
  assets['mislabelled.mp3'] = assets['source.aac'];
  assets['broken.aac'] = Buffer.from('invalid audio');
  assets['bad-cover.jpg'] = Buffer.from('invalid cover');
  const contentTypes = { aac: 'audio/aac', m4a: 'audio/mp4', mp3: 'audio/mpeg', flac: 'audio/flac' };
  server = createServer((request, response) => {
    const name = request.url.slice(1);
    const data = assets[name];
    if (!data) { response.writeHead(404); response.end(); return; }
    response.writeHead(200, {
      'Content-Type': contentTypes[name.split('.').pop()] || 'application/octet-stream',
      'Content-Length': data.length,
    });
    response.end(data);
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  baseUrl = `http://127.0.0.1:${server.address().port}`;
  const provider = getProvider('gequbao');
  originalGetPlayInfo = provider.getPlayInfo;
  provider.getPlayInfo = async (id) => playInfo(id);
  originalEnv = { ENABLE_DOWNLOAD: process.env.ENABLE_DOWNLOAD, SAVE_TO_NAS: process.env.SAVE_TO_NAS, MUSIC_LIBRARY_DIR: process.env.MUSIC_LIBRARY_DIR };
  process.env.ENABLE_DOWNLOAD = '1';
  process.env.SAVE_TO_NAS = '1';
  process.env.MUSIC_LIBRARY_DIR = join(root, 'library');
});

after(async () => {
  if (originalGetPlayInfo) getProvider('gequbao').getPlayInfo = originalGetPlayInfo;
  for (const [key, value] of Object.entries(originalEnv || {})) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  if (server) await new Promise(resolve => server.close(resolve));
  if (root) await rm(root, { recursive: true, force: true });
});

test('format hints and output filenames are normalized', () => {
  assert.equal(getAudioExtension({ url: 'https://example.invalid/song.AAC?x=1', type: 'mp3' }), 'aac');
  assert.equal(getAudioExtension({ url: 'https://example.invalid/download.php', type: 'flac' }), 'flac');
  assert.equal(getAudioExtension({ url: 'https://example.invalid/song', type: 'mp3' }, 'audio/aac; charset=binary'), 'aac');
  assert.equal(getDownloadFilename('歌手 - 歌名.M4A', 'mp3'), '歌手 - 歌名.mp3');
});

for (const name of ['source.aac', 'source.m4a', 'mislabelled.mp3']) {
  test(`browser converts actual AAC from ${name}`, async () => {
    const response = await browserDownload(name, true);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('content-type'), 'audio/mpeg');
    assert.match(response.headers.get('content-disposition'), /\.mp3/);
    const data = Buffer.from(await response.arrayBuffer());
    assert.equal(Number(response.headers.get('content-length')), data.length);
    const path = join(root, 'browser.mp3');
    await writeFile(path, data);
    assert.equal((await probe(path)).streams[0].codec_name, 'mp3');
  });
}

for (const name of ['source.mp3', 'source.flac', 'alac.m4a']) {
  test(`enabled conversion preserves non-AAC bytes for ${name}`, async () => {
    const response = await browserDownload(name, true);
    assert.equal(response.status, 200);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), assets[name]);
    assert.match(response.headers.get('content-disposition'), new RegExp(`\\.${name.split('.').pop()}`));
  });
}

for (const enabled of [false, undefined]) {
  test(`browser preserves AAC when conversion is ${enabled}`, async () => {
    const response = await browserDownload('source.aac', enabled);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('content-type'), 'audio/aac');
    assert.match(response.headers.get('content-disposition'), /\.aac/);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), assets['source.aac']);
  });
}

test('POST saves converted MP3 with tags and lyrics to NAS', async () => {
  const request = new NextRequest('http://localhost/api/download', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...musicItem, id: 'source.m4a', saveToNas: true, convertAacToMp3: true }),
  });
  const response = await POST(request);
  assert.equal(response.status, 200);
  const { saved } = await response.json();
  assert.match(saved.audioPath, /\.mp3$/);
  const info = await probe(saved.audioPath);
  assert.equal(info.streams[0].codec_name, 'mp3');
  assert.equal(info.format.tags.title, musicItem.title);
  assert.equal(info.format.tags.artist, musicItem.artist);
  assert.equal(await readFile(saved.lyricsPath, 'utf8'), '[00:00.00]测试歌词');
});

test('NAS disabled conversion keeps AAC and non-AAC retains its codec', async () => {
  for (const [name, enabled, codec] of [['source.aac', false, 'aac'], ['source.flac', true, 'flac'], ['alac.m4a', true, 'alac']]) {
    const saved = await saveMusicToLibrary({ libraryRoot: join(root, 'originals'), musicItem, playInfo: playInfo(name), sourceUrl: `${baseUrl}/${name}`, convertAacToMp3: enabled });
    assert.match(saved.audioPath, new RegExp(`\\.${name.split('.').pop()}$`));
    assert.equal((await probe(saved.audioPath)).streams[0].codec_name, codec);
  }
});

test('optional cover/tagging failures retain real MP3, not renamed AAC', async () => {
  for (const cover of ['bad-cover.jpg', 'missing.jpg']) {
    const saved = await saveMusicToLibrary({ libraryRoot: join(root, 'cover-fallback'), musicItem, playInfo: { ...playInfo('source.aac'), cover: `${baseUrl}/${cover}` }, sourceUrl: `${baseUrl}/source.aac`, convertAacToMp3: true });
    assert.match(saved.audioPath, /\.mp3$/);
    assert.equal((await probe(saved.audioPath)).streams[0].codec_name, 'mp3');
  }
});

test('probe failures are visible and do not overwrite existing NAS files', async () => {
  const expectedPath = join(root, 'library', '测试歌手 - 测试歌曲.mp3');
  const previous = await readFile(expectedPath);
  await assert.rejects(saveMusicToLibrary({ libraryRoot: join(root, 'library'), musicItem, playInfo: playInfo('broken.aac'), sourceUrl: `${baseUrl}/broken.aac`, convertAacToMp3: true }), AudioConversionError);
  assert.deepEqual(await readFile(expectedPath), previous);
  const response = await browserDownload('broken.aac', true);
  assert.equal(response.status, 500);
  assert.match((await response.json()).error, /ffprobe/);
});

test('ffmpeg failure is not treated as optional tagging failure', async () => {
  const { stdout } = await exec('which', ['ffprobe']);
  const tools = join(root, 'probe-only');
  await mkdir(tools);
  await copyFile(stdout.trim(), join(tools, 'ffprobe'));
  const originalPath = process.env.PATH;
  process.env.PATH = tools;
  try {
    await assert.rejects(prepareAudioFile(join(root, 'source.aac'), 'aac', true), /AAC 转 MP3 失败/);
    await assert.rejects(saveMusicToLibrary({ libraryRoot: join(root, 'failed-conversion'), musicItem, playInfo: playInfo('source.aac'), sourceUrl: `${baseUrl}/source.aac`, convertAacToMp3: true }), /AAC 转 MP3 失败/);
    assert.deepEqual(await readdir(join(root, 'failed-conversion')), []);
  } finally {
    process.env.PATH = originalPath;
  }
});

test('missing conversion tools fail explicitly; disabled conversion needs neither', async () => {
  const originalPath = process.env.PATH;
  process.env.PATH = root;
  try {
    await assert.rejects(prepareAudioFile(join(root, 'source.aac'), 'aac', true), AudioConversionError);
    assert.deepEqual(await prepareAudioFile(join(root, 'source.aac'), 'aac', false), { audioPath: join(root, 'source.aac'), extension: 'aac' });
  } finally {
    process.env.PATH = originalPath;
  }
});

test('conversion-disabled browser download does not write to configured NAS', async () => {
  const before = await readdir(join(root, 'library'));
  const response = await browserDownload('source.aac', false, 'browser-only.mp3');
  await response.arrayBuffer();
  assert.deepEqual(await readdir(join(root, 'library')), before);
});
