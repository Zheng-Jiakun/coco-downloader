import { NextRequest, NextResponse } from "next/server";
import axios from "axios";
import { Readable } from "stream";
import { createReadStream, createWriteStream } from "fs";
import { mkdtemp, rm, stat } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";
import { pipeline } from "stream/promises";
import { getProvider } from "@/lib/providers";
import { getMusicLibraryRoot, saveMusicToLibrary } from "@/lib/download";
import { AudioConversionError, getAudioContentType, getAudioExtension, getDownloadFilename, prepareAudioFile } from "@/lib/audio";
import { providerErrorMessage } from "@/lib/api-error";

const DOWNLOAD_TIMEOUT = 30000;
const RETRY_LIMIT = 2;
const RETRY_DELAY = 600;

export const runtime = "nodejs";

function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isRetryableError(error: unknown) {
  const err = error as { code?: string; message?: string };
  const code = err?.code || "";
  const message = err?.message || "";
  return (
    code === "ETIMEDOUT" ||
    code === "ECONNABORTED" ||
    code === "UND_ERR_CONNECT_TIMEOUT" ||
    message.toLowerCase().includes("timeout")
  );
}

function parseExtra(value: string | null) {
  if (!value) return undefined;
  try {
    return JSON.parse(value) as unknown;
  } catch {
    return undefined;
  }
}

async function requestAudioStream(url: string, attempt = 0) {
  try {
    const response = await axios.get(url, {
      responseType: "stream",
      timeout: DOWNLOAD_TIMEOUT,
      maxRedirects: 5,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
      },
      validateStatus: () => true,
    });

    if (response.status < 200 || response.status >= 300) {
      response.data.destroy();
      throw new Error(`Upstream error: ${response.status}`);
    }

    if (/^(application\/json|text\/)/i.test(String(response.headers['content-type'] || ''))) {
      response.data.destroy();
      throw new Error('渠道未返回有效音频，请重试或切换渠道');
    }

    return { stream: response.data as Readable, headers: response.headers as Record<string, string | undefined> };
  } catch (error) {
    if (attempt < RETRY_LIMIT && isRetryableError(error)) {
      await delay(RETRY_DELAY * (attempt + 1));
      return requestAudioStream(url, attempt + 1);
    }
    throw error;
  }
}

type DownloadPayload = {
  id?: string;
  filename?: string;
  provider?: string;
  extra?: unknown;
  title?: string;
  artist?: string;
  album?: string;
  cover?: string;
  lyrics?: string;
  convertAacToMp3?: boolean;
  saveToNas?: boolean;
};

function readBoolean(value: string | null) {
  if (value === '1' || value === 'true') return true;
  if (value === '0' || value === 'false') return false;
  return undefined;
}

async function readPayload(request: NextRequest): Promise<DownloadPayload> {
  const searchParams = request.nextUrl.searchParams;
  const queryPayload: DownloadPayload = {
    id: searchParams.get("id") || undefined,
    filename: searchParams.get("filename") || undefined,
    provider: searchParams.get("provider") || undefined,
    extra: parseExtra(searchParams.get("extra")),
    title: searchParams.get("title") || undefined,
    artist: searchParams.get("artist") || undefined,
    album: searchParams.get("album") || undefined,
    cover: searchParams.get("cover") || undefined,
    lyrics: searchParams.get("lyrics") || undefined,
    convertAacToMp3: readBoolean(searchParams.get("convertAacToMp3")),
    saveToNas: readBoolean(searchParams.get("saveToNas")),
  };

  if (request.method !== "POST") {
    return queryPayload;
  }

  try {
    const body = (await request.json()) as Partial<DownloadPayload>;
    return { ...queryPayload, ...body };
  } catch {
    return queryPayload;
  }
}

export async function GET(request: NextRequest) {
  return handleDownload(request);
}

export async function POST(request: NextRequest) {
  return handleDownload(request);
}

async function handleDownload(request: NextRequest) {
  const payload = await readPayload(request);
  const searchParams = request.nextUrl.searchParams;
  const id = payload.id || searchParams.get("id");
  const filename = payload.filename || searchParams.get("filename");
  const providerName = payload.provider || searchParams.get("provider") || "netease";
  const extra = payload.extra;

  if (!id) {
    return NextResponse.json({ error: "Missing id" }, { status: 400 });
  }

  try {
    // 1. 获取真实播放地址
    const provider = getProvider(providerName);
    const playInfo = await provider.getPlayInfo(id, extra);
    if (!playInfo || !playInfo.url) {
      return NextResponse.json({ error: "Failed to get url" }, { status: 404 });
    }

    const downloadEnabled = process.env.ENABLE_DOWNLOAD !== "0";
    if (!downloadEnabled) {
      return NextResponse.json(
        { error: "Download disabled", url: playInfo.url },
        { status: 503 }
      );
    }

    const libraryRoot = getMusicLibraryRoot();
    const saveToNasEnabled = Boolean(libraryRoot) && (process.env.SAVE_TO_NAS ?? "1") !== "0" && payload.saveToNas !== false;

    if (saveToNasEnabled) {
      const saved = await saveMusicToLibrary({
        libraryRoot,
        musicItem: {
          id,
          title: payload.title || filename || `music-${id}`,
          artist: payload.artist || "未知歌手",
          album: payload.album || undefined,
          cover: payload.cover || playInfo.cover,
          provider: providerName,
        },
        playInfo: {
          ...playInfo,
          cover: payload.cover || playInfo.cover,
          lyrics: payload.lyrics || playInfo.lyrics,
        },
        sourceUrl: playInfo.url,
        convertAacToMp3: payload.convertAacToMp3 === true,
      });

      return NextResponse.json({ ok: true, saved });
    }

    const { stream, headers: upstreamHeaders } = await requestAudioStream(playInfo.url);
    let extension = getAudioExtension(playInfo, upstreamHeaders['content-type']);
    let responseStream = stream;
    let contentLength = upstreamHeaders['content-length'];

    if (payload.convertAacToMp3 === true) {
      let tempDir: string | undefined;
      try {
        tempDir = await mkdtemp(join(tmpdir(), 'coco-download-'));
        const inputPath = join(tempDir, 'source');
        await pipeline(stream, createWriteStream(inputPath));
        const prepared = await prepareAudioFile(inputPath, extension, true);
        extension = prepared.extension;
        contentLength = String((await stat(prepared.audioPath)).size);
        const fileStream = createReadStream(prepared.audioPath);
        const completedTempDir = tempDir;
        fileStream.once('close', () => {
          void rm(completedTempDir, { recursive: true, force: true }).catch(() => undefined);
        });
        responseStream = fileStream;
      } catch (error) {
        stream.destroy();
        if (tempDir) await rm(tempDir, { recursive: true, force: true }).catch(() => undefined);
        throw error;
      }
    }

    const headers = new Headers();
    headers.set('Content-Type', getAudioContentType(extension));
    if (contentLength) headers.set('Content-Length', contentLength);
    const downloadFilename = getDownloadFilename(filename || `music-${id}`, extension);
    const safeFilename = encodeURIComponent(downloadFilename).replace(/'/g, '%27');
    headers.set('Content-Disposition', `attachment; filename="${safeFilename}"; filename*=UTF-8''${safeFilename}`);

    return new NextResponse(Readable.toWeb(responseStream) as ReadableStream<Uint8Array>, {
      status: 200,
      headers,
    });

  } catch (error) {
    console.error("Download error:", error);
    return NextResponse.json(
      { error: providerErrorMessage(error) },
      { status: error instanceof AudioConversionError ? 500 : 502 },
    );
  }
}
