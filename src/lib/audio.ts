import { execFile } from 'child_process';
import { dirname, join } from 'path';
import { promisify } from 'util';

import type { PlayInfo } from '@/types/music';

const execFileAsync = promisify(execFile);
const AUDIO_EXTENSIONS = new Set(['mp3', 'aac', 'm4a', 'mp4', 'flac', 'ogg', 'opus', 'wav', 'aiff', 'wma']);
const MIME_EXTENSIONS: Record<string, string> = {
  'audio/mpeg': 'mp3',
  'audio/mp3': 'mp3',
  'audio/aac': 'aac',
  'audio/aacp': 'aac',
  'audio/x-aac': 'aac',
  'audio/mp4': 'm4a',
  'audio/x-m4a': 'm4a',
  'audio/flac': 'flac',
  'audio/x-flac': 'flac',
  'audio/ogg': 'ogg',
  'audio/opus': 'opus',
  'audio/wav': 'wav',
  'audio/x-wav': 'wav',
};

export class AudioConversionError extends Error {}

export function getAudioExtension(playInfo: PlayInfo, contentType?: string) {
  const mimeExtension = MIME_EXTENSIONS[contentType?.split(';')[0].trim().toLowerCase() || ''];
  if (mimeExtension) return mimeExtension;

  try {
    const extension = new URL(playInfo.url).pathname.split('.').pop()?.toLowerCase();
    if (extension && AUDIO_EXTENSIONS.has(extension)) return extension;
  } catch {
    // Some providers only supply a format hint.
  }

  const type = playInfo.type.toLowerCase();
  return AUDIO_EXTENSIONS.has(type) ? type : 'mp3';
}

export function getAudioContentType(extension: string) {
  return Object.entries(MIME_EXTENSIONS).find(([, value]) => value === extension)?.[0]
    || 'application/octet-stream';
}

export function getDownloadFilename(filename: string, extension: string) {
  return `${filename.replace(/\.(mp3|aac|m4a|mp4|flac|ogg|opus|wav|aiff|wma)$/i, '')}.${extension}`;
}

export async function prepareAudioFile(inputPath: string, extension: string, convertAacToMp3: boolean) {
  if (!convertAacToMp3) return { audioPath: inputPath, extension };

  let codec: string | undefined;
  let format: string | undefined;
  try {
    const { stdout } = await execFileAsync('ffprobe', [
      '-v', 'error', '-select_streams', 'a:0',
      '-show_entries', 'stream=codec_name:format=format_name', '-of', 'json', inputPath,
    ], { timeout: 30000 });
    const info = JSON.parse(stdout) as {
      streams?: { codec_name?: string }[];
      format?: { format_name?: string };
    };
    codec = info.streams?.[0]?.codec_name;
    format = info.format?.format_name;
    if (!codec) throw new Error('No audio stream');
  } catch (error) {
    throw new AudioConversionError('无法检测音频编码，请确认服务器已安装 ffprobe，或关闭 AAC 自动转 MP3。', { cause: error });
  }

  if (codec !== 'aac') {
    const formats = format?.split(',') || [];
    const detectedExtension = formats.includes('mp4') ? 'm4a' : formats.find(value => AUDIO_EXTENSIONS.has(value));
    return { audioPath: inputPath, extension: detectedExtension || extension };
  }

  const outputPath = join(dirname(inputPath), 'converted.mp3');
  try {
    await execFileAsync('ffmpeg', [
      '-nostdin', '-y', '-v', 'error', '-i', inputPath,
      '-map', '0:a:0', '-map_metadata', '0', '-vn',
      '-c:a', 'libmp3lame', '-q:a', '2', '-id3v2_version', '3',
      '-f', 'mp3', outputPath,
    ], { timeout: 300000 });
  } catch (error) {
    throw new AudioConversionError('AAC 转 MP3 失败，请确认服务器的 ffmpeg 支持 libmp3lame，或关闭自动转换后重试。', { cause: error });
  }

  return { audioPath: outputPath, extension: 'mp3' };
}
