import axios from 'axios';
import { spawn } from 'child_process';
import { createWriteStream } from 'fs';
import { copyFile, mkdtemp, mkdir, rm, writeFile } from 'fs/promises';
import { extname, join } from 'path';
import { tmpdir } from 'os';
import { pipeline } from 'stream/promises';

import type { MusicItem, PlayInfo } from '@/types/music';
import { getAudioExtension, prepareAudioFile } from './audio';

export interface SaveMusicInput {
  libraryRoot: string;
  musicItem: MusicItem;
  playInfo: PlayInfo;
  sourceUrl: string;
  convertAacToMp3?: boolean;
}

export interface SavedMusicResult {
  audioPath: string;
  lyricsPath?: string;
}

function normalizeWhitespace(value: string) {
  return value.replace(/\s+/g, ' ').trim();
}

export function sanitizePathSegment(value: string | undefined, fallback: string) {
  const normalized = normalizeWhitespace(String(value ?? ''));
  const cleaned = normalized
    .replace(/[\\/:*?"<>|]/g, '_')
    .replace(/[\u0000-\u001f]/g, '')
    .replace(/\.+$/g, '')
    .trim();
  return cleaned || fallback;
}

export function sanitizeFileBaseName(value: string | undefined, fallback: string) {
  return sanitizePathSegment(value, fallback).replace(/\s+/g, ' ');
}

export function getMusicLibraryRoot() {
  const candidates = [
    process.env.MUSIC_LIBRARY_DIR,
    process.env.NAS_MUSIC_DIR,
    process.env.DOWNLOAD_TARGET_DIR,
  ];

  for (const candidate of candidates) {
    const value = candidate?.trim();
    if (value) {
      return value;
    }
  }

  return '';
}

function getExtensionFromUrl(url: string, fallback = 'mp3') {
  try {
    const pathname = new URL(url).pathname;
    const ext = extname(pathname).replace('.', '').toLowerCase();
    return ext || fallback;
  } catch {
    return fallback;
  }
}

function getBaseName(musicItem: MusicItem) {
  const artist = sanitizeFileBaseName(musicItem.artist, 'Unknown Artist');
  const title = sanitizeFileBaseName(musicItem.title, 'Unknown Title');
  return `${artist} - ${title}`;
}

export function buildMusicLibraryPaths(libraryRoot: string, musicItem: MusicItem, playInfo: PlayInfo, outputExt = getAudioExtension(playInfo)) {
  const baseName = getBaseName(musicItem);

  return {
    audioPath: join(libraryRoot, `${baseName}.${outputExt}`),
    lyricsPath: join(libraryRoot, `${baseName}.lrc`),
    outputExt,
  };
}


async function downloadBinary(url: string, targetPath: string, audioOnly = false) {
  const response = await axios.get(url, {
    responseType: 'stream',
    timeout: 30000,
    maxRedirects: 5,
    headers: {
      'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    },
    validateStatus: () => true,
  });

  if (response.status < 200 || response.status >= 300) {
    response.data.destroy();
    throw new Error(`Failed to download asset: ${response.status}`);
  }

  if (audioOnly && /^(application\/json|text\/)/i.test(String(response.headers['content-type'] || ''))) {
    response.data.destroy();
    throw new Error('渠道未返回有效音频，请重试或切换渠道');
  }

  await pipeline(response.data, createWriteStream(targetPath));
  return response.headers['content-type'] as string | undefined;
}

function runFfmpeg(args: string[]) {
  return new Promise<void>((resolvePromise, rejectPromise) => {
    const child = spawn('ffmpeg', args, { stdio: ['ignore', 'ignore', 'pipe'] });
    let stderr = '';

    child.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
    });

    child.on('error', (error) => rejectPromise(error));
    child.on('close', (code) => {
      if (code === 0) {
        resolvePromise();
        return;
      }
      rejectPromise(new Error(stderr || `ffmpeg exited with code ${code}`));
    });
  });
}

async function processWithFfmpeg(inputAudioPath: string, outputAudioPath: string, coverPath?: string, metadata?: { title: string; artist: string; album?: string; lyrics?: string }) {
  const args = ['-y', '-i', inputAudioPath];

  if (coverPath) {
    args.push('-i', coverPath);
    args.push('-map', '0:a', '-map', '1:v');
    args.push('-c:a', 'copy', '-c:v', 'mjpeg', '-disposition:v:0', 'attached_pic');
  } else {
    args.push('-map', '0:a', '-c:a', 'copy');
  }

  if (metadata) {
    args.push('-metadata', `title=${metadata.title}`);
    args.push('-metadata', `artist=${metadata.artist}`);
    args.push('-metadata', `album=${metadata.album || 'Singles'}`);
    args.push('-metadata', `album_artist=${metadata.artist}`);
    if (metadata.lyrics) {
      args.push('-metadata', `comment=${metadata.lyrics}`);
    }
  }

  args.push(outputAudioPath);
  await runFfmpeg(args);
}

export async function saveMusicToLibrary(input: SaveMusicInput): Promise<SavedMusicResult> {
  const libraryRoot = input.libraryRoot.trim();
  if (!libraryRoot) {
    throw new Error('Missing music library root');
  }

  await mkdir(libraryRoot, { recursive: true });

  const tempDir = await mkdtemp(join(tmpdir(), 'coco-downloader-'));
  const tempAudioPath = join(tempDir, 'source');

  try {
    const contentType = await downloadBinary(input.sourceUrl, tempAudioPath, true);
    const prepared = await prepareAudioFile(
      tempAudioPath,
      getAudioExtension(input.playInfo, contentType),
      input.convertAacToMp3 ?? false,
    );
    const paths = buildMusicLibraryPaths(libraryRoot, input.musicItem, input.playInfo, prepared.extension);
    const finalAudioPath = paths.audioPath;
    const taggedAudioPath = join(tempDir, `tagged.${paths.outputExt}`);

    let downloadedCoverPath: string | undefined;
    const coverUrl = input.playInfo.cover || input.musicItem.cover;
    if (coverUrl && coverUrl.startsWith('http')) {
      const coverExt = getExtensionFromUrl(coverUrl, 'jpg');
      downloadedCoverPath = join(tempDir, `cover.${coverExt}`);
      try {
        await downloadBinary(coverUrl, downloadedCoverPath);
      } catch {
        downloadedCoverPath = undefined;
      }
    }

    let completedAudioPath = prepared.audioPath;
    try {
      await processWithFfmpeg(
        prepared.audioPath,
        taggedAudioPath,
        downloadedCoverPath,
        {
          title: sanitizeFileBaseName(input.musicItem.title, 'Unknown Title'),
          artist: sanitizeFileBaseName(input.musicItem.artist, 'Unknown Artist'),
          album: sanitizeFileBaseName(input.musicItem.album, 'Singles'),
          lyrics: input.playInfo.lyrics,
        }
      );
      completedAudioPath = taggedAudioPath;
    } catch {
      // Tagging is optional; keep the prepared audio, never AAC under an MP3 name.
    }
    await copyFile(completedAudioPath, finalAudioPath);

    let savedLyricsPath: string | undefined;
    if (input.playInfo.lyrics) {
      savedLyricsPath = paths.lyricsPath;
      await writeFile(savedLyricsPath, input.playInfo.lyrics.replace(/\r?\n/g, '\n'));
    }

    return {
      audioPath: finalAudioPath,
      lyricsPath: savedLyricsPath,
    };
  } finally {
    await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
  }
}
