import axios from 'axios';
import { MusicItem, MusicProvider, PlayInfo } from '@/types/music';

const BASE_URL = 'https://music.wjhe.top';
const REQUEST_TIMEOUT = 20000;

const HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
  'Referer': `${BASE_URL}/`,
  'Accept': 'application/json, text/javascript, */*; q=0.01',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
  'X-Requested-With': 'XMLHttpRequest',
  'Sec-Fetch-Dest': 'empty',
  'Sec-Fetch-Mode': 'cors',
  'Sec-Fetch-Site': 'same-origin',
  'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
};

type JooxFileLink = {
  quality?: string | number;
  format?: string;
};

type JooxSearchItem = {
  ID?: string | number;
  name?: string;
  title?: string;
  duration?: number;
  fileLinks?: JooxFileLink[];
  singers?: Array<{ name?: string }>;
  album?: { name?: string };
};

type JooxExtra = {
  source: 'joox';
  fileLinks: JooxFileLink[];
  selectedQuality?: string;
  selectedFormat?: string;
  qualityOptions: Array<{
    value: string;
    label: string;
    quality: string;
    format: string;
  }>;
};

function secondsToHms(seconds?: number | null) {
  if (seconds == null) return undefined;
  const total = Math.floor(Number(seconds));
  const hour = Math.floor(total / 3600);
  const minute = Math.floor((total % 3600) / 60);
  const second = total % 60;
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}`;
}

function getResponseUrl(response: unknown) {
  const request = response as { request?: { res?: { responseUrl?: string }; path?: string } };
  const resUrl = request?.request?.res?.responseUrl;
  if (typeof resUrl === 'string' && resUrl.startsWith('http')) return resUrl;
  return '';
}

function pickBestFileLink(fileLinks: JooxFileLink[]) {
  const candidates = fileLinks.filter((item) => item && item.quality != null && item.format);
  if (candidates.length === 0) return undefined;
  return [...candidates].sort((a, b) => Number(b.quality || 0) - Number(a.quality || 0))[0];
}

function buildQualityOptions(fileLinks: JooxFileLink[]) {
  return fileLinks
    .filter((item) => item && item.quality != null && item.format)
    .sort((a, b) => Number(b.quality || 0) - Number(a.quality || 0))
    .map((item) => {
      const quality = String(item.quality);
      const format = String(item.format);
      return {
        value: `${quality}:${format}`,
        label: `${quality} ${format}`.toUpperCase(),
        quality,
        format,
      };
    });
}

function extractExt(url: string, fallback = 'mp3') {
  const clean = url.split('?')[0];
  const parts = clean.split('.');
  return parts.length > 1 ? parts[parts.length - 1] : fallback;
}

export class JooxProvider implements MusicProvider {
  name = 'joox';

  async search(query: string): Promise<MusicItem[]> {
    try {
      const { data } = await axios.get(`${BASE_URL}/api/music/joox/search`, {
        headers: HEADERS,
        params: {
          key: query.trim(),
          pageIndex: '1',
          pageSize: '10',
          _: String(Date.now()),
        },
        timeout: REQUEST_TIMEOUT,
      });

      const items = ((((data || {}).data || {}).data) || []) as JooxSearchItem[];
      const results: MusicItem[] = [];
      for (const item of items) {
        const fileLinks = Array.isArray(item.fileLinks) ? item.fileLinks : [];
        if (!item.ID || fileLinks.length === 0) continue;

        const qualityOptions = buildQualityOptions(fileLinks);
        const bestLink = pickBestFileLink(fileLinks);
        const artists = (item.singers || [])
          .map((singer) => String(singer?.name || '').trim())
          .filter(Boolean)
          .join(', ');
        const title = String(item.name || item.title || '').trim();
        if (!title) continue;

        results.push({
          id: String(item.ID),
          title,
          artist: artists || '未知歌手',
          album: item.album?.name || undefined,
          duration: secondsToHms(item.duration),
          provider: this.name,
          extra: {
            source: 'joox',
            fileLinks,
            selectedQuality: bestLink?.quality != null ? String(bestLink.quality) : undefined,
            selectedFormat: bestLink?.format ? String(bestLink.format) : undefined,
            qualityOptions,
          } satisfies JooxExtra,
        });
      }
      return results;
    } catch (error) {
      console.error('Joox search error:', error);
      return [];
    }
  }

  async getPlayInfo(id: string, extra?: unknown): Promise<PlayInfo> {
    try {
      const payload = (extra || {}) as Partial<JooxExtra>;
      const fileLinks = Array.isArray(payload.fileLinks) ? payload.fileLinks : [];
      const preferred =
        fileLinks.find(
          (item) =>
            String(item?.quality || '') === String(payload.selectedQuality || '') &&
            String(item?.format || '') === String(payload.selectedFormat || '')
        ) || pickBestFileLink(fileLinks);

      if (!preferred?.quality || !preferred?.format) {
        throw new Error('Missing joox quality info');
      }

      const coverResponse = await axios.head(`${BASE_URL}/api/music/joox/url`, {
        headers: HEADERS,
        params: {
          ID: id,
          quality: '500',
          format: 'jpg',
        },
        maxRedirects: 5,
        timeout: 10000,
      });

      const response = await axios.head(`${BASE_URL}/api/music/joox/url`, {
        headers: HEADERS,
        params: {
          ID: id,
          quality: String(preferred.quality),
          format: String(preferred.format),
        },
        maxRedirects: 5,
        timeout: REQUEST_TIMEOUT,
      });

      const url = getResponseUrl(response);
      if (!url.startsWith('http')) {
        throw new Error('Invalid joox play url');
      }

      const cover = getResponseUrl(coverResponse);
      return {
        url,
        type: extractExt(url, String(preferred.format).toLowerCase()),
        cover: cover.startsWith('http') ? cover : undefined,
        bitrate: `${preferred.quality} ${preferred.format}`.toUpperCase(),
      };
    } catch (error) {
      console.error('Joox getPlayInfo error:', error);
      throw error;
    }
  }
}
