import axios from 'axios';
import https from 'https';
import { MusicItem, MusicProvider, PlayInfo } from '@/types/music';

const SEARCH_HEADERS = {
  accept: 'application/json, text/plain, */*',
  'accept-encoding': 'gzip, deflate, br, zstd',
  'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
  origin: 'https://buguyy.top',
  priority: 'u=1, i',
  referer: 'https://buguyy.top/',
  'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-site',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
};

const REQUEST_TIMEOUT = 20000;
const HTTPS_AGENT = new https.Agent({ rejectUnauthorized: false });

type BuguSearchItem = {
  id?: string | number;
  title?: string;
  singer?: string;
  album?: string;
  picurl?: string;
  duration?: string | number;
};

type BuguSearchResponse = {
  data?: {
    list?: BuguSearchItem[];
  };
};

type BuguDetailResponse = {
  data?: {
    url?: string;
    lrc?: string;
    duration?: string | number;
    album?: string;
  };
};

export type BuguLyricData = {
  songid: string;
  provider: 'bugu';
  lines: Array<{ time: number; text: string }>;
  lrc: string;
};

function normalizeDuration(value: unknown): string | undefined {
  if (value === null || value === undefined) return undefined;
  const parts = String(value).match(/\d+/g) || [];
  if (!parts.length) return undefined;
  const numbers = parts.map((part) => Number(part)).filter((n) => Number.isFinite(n));
  if (!numbers.length) return undefined;
  const lastThree = numbers.slice(-3);
  while (lastThree.length < 3) {
    lastThree.unshift(0);
  }
  const [hours, minutes, seconds] = lastThree;
  if (hours === 0 && minutes === 0 && seconds === 0) return undefined;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

function decodeHtmlEntities(value: string) {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, ' ');
}

function cleanLyric(value: unknown) {
  if (typeof value !== 'string') return '';
  const lyric = decodeHtmlEntities(value)
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/\r\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  return lyric && !lyric.includes('歌词获取失败') ? lyric : '';
}

function parseLyricLines(lyric: string) {
  const lines: Array<{ time: number; text: string }> = [];
  const timePattern = /\[(\d{1,2}):(\d{1,2})(?:\.(\d{1,3}))?\]/g;

  for (const rawLine of lyric.split(/\r?\n/)) {
    const matches = [...rawLine.matchAll(timePattern)];
    if (matches.length === 0) continue;

    const text = rawLine.replace(timePattern, '').trim();
    for (const match of matches) {
      const minutes = Number(match[1]);
      const seconds = Number(match[2]);
      const fraction = match[3] ? Number(match[3].padEnd(3, '0').slice(0, 3)) / 1000 : 0;
      lines.push({ time: minutes * 60 + seconds + fraction, text });
    }
  }

  return lines
    .filter((line) => line.text)
    .sort((a, b) => a.time - b.time);
}

function extractExt(url: string) {
  const clean = url.split('?')[0];
  const parts = clean.split('.');
  return parts.length > 1 ? parts[parts.length - 1] : 'mp3';
}

export class BuguProvider implements MusicProvider {
  name = 'bugu';

  async search(query: string): Promise<MusicItem[]> {
    try {
      const { data } = await axios.get<BuguSearchResponse>('https://a.buguyy.top/newapi/search.php', {
        headers: SEARCH_HEADERS,
        params: { keyword: query },
        timeout: REQUEST_TIMEOUT,
        httpsAgent: HTTPS_AGENT,
      });
      const list = data?.data?.list || [];
      return list
        .map((item) => ({
          id: String(item?.id ?? ''),
          title: item?.title || '未知歌曲',
          artist: item?.singer || '未知歌手',
          album: item?.album || undefined,
          cover: item?.picurl || undefined,
          duration: normalizeDuration(item?.duration),
          provider: this.name,
          extra: {
            cover: item?.picurl || undefined,
          },
        }))
        .filter((item) => item.id);
    } catch (error) {
      console.error('Bugu search error:', error);
      return [];
    }
  }

  async getPlayInfo(id: string, extra?: unknown): Promise<PlayInfo> {
    try {
      const { data } = await axios.get<BuguDetailResponse>('https://a.buguyy.top/newapi/geturl2.php', {
        headers: SEARCH_HEADERS,
        params: { id },
        timeout: REQUEST_TIMEOUT,
        httpsAgent: HTTPS_AGENT,
      });
      const url = data?.data?.url;
      if (typeof url !== 'string' || !url.startsWith('http')) {
        throw new Error('Failed to get play url');
      }
      const coverCandidate = (extra as { cover?: unknown } | undefined)?.cover;
      return {
        url,
        type: extractExt(url),
        cover: typeof coverCandidate === 'string' ? coverCandidate : undefined,
        lyrics: typeof data?.data?.lrc === 'string' && data.data.lrc.trim() ? data.data.lrc : undefined,
      };
    } catch (error) {
      console.error('Bugu getPlayInfo error:', error);
      throw error;
    }
  }

  async getLyric(id: string): Promise<BuguLyricData> {
    const { data } = await axios.get<BuguDetailResponse>('https://a.buguyy.top/newapi/geturl2.php', {
      headers: SEARCH_HEADERS,
      params: { id },
      timeout: REQUEST_TIMEOUT,
      httpsAgent: HTTPS_AGENT,
    });
    const lrc = cleanLyric(data?.data?.lrc);

    return {
      songid: id,
      provider: 'bugu',
      lines: parseLyricLines(lrc),
      lrc,
    };
  }
}
