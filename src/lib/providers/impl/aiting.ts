import axios from 'axios';
import * as cheerio from 'cheerio';
import { MusicItem, MusicProvider, PlayInfo } from '@/types/music';

const BASE_URL = 'https://www.2t58.com';
const REQUEST_TIMEOUT = 20000;

const PAGE_HEADERS = {
  'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
  'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
  'cache-control': 'max-age=0',
  'origin': BASE_URL,
  'priority': 'u=0, i',
  'referer': `${BASE_URL}/`,
  'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'document',
  'sec-fetch-mode': 'navigate',
  'sec-fetch-site': 'same-origin',
  'sec-fetch-user': '?1',
  'upgrade-insecure-requests': '1',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
};

function cleanText(value?: string | null) {
  return (value || '').replace(/\s+/g, ' ').trim();
}

function extractSongId(value: string) {
  const match = value.match(/\/song\/([^/?#]+)\.html/i);
  if (match) return match[1];
  return value.replace(/^\/+|\/+$/g, '').replace(/\.html$/i, '');
}

function extractExt(url: string) {
  const clean = url.split('?')[0];
  const parts = clean.split('.');
  return parts.length > 1 ? parts[parts.length - 1] : 'mp3';
}

function absoluteUrl(value?: string | null) {
  if (!value) return undefined;
  try {
    return new URL(value, `${BASE_URL}/`).toString();
  } catch {
    return value || undefined;
  }
}

function parseSetCookie(setCookie?: string[]) {
  if (!Array.isArray(setCookie) || setCookie.length === 0) return '';
  return setCookie
    .map((item) => item.split(';', 1)[0]?.trim())
    .filter(Boolean)
    .join('; ');
}

function safeJson(payload: unknown) {
  if (typeof payload === 'string') {
    return JSON.parse(payload) as Record<string, unknown>;
  }
  return payload as Record<string, unknown>;
}

export class AitingProvider implements MusicProvider {
  name = 'aiting';

  private async bootstrapCookie() {
    try {
      const response = await axios.get(`${BASE_URL}/`, {
        headers: PAGE_HEADERS,
        timeout: REQUEST_TIMEOUT,
      });
      return parseSetCookie(response.headers['set-cookie']);
    } catch {
      return '';
    }
  }

  async search(query: string): Promise<MusicItem[]> {
    try {
      const cookie = await this.bootstrapCookie();
      const url = `${BASE_URL}/so/${encodeURIComponent(query.trim())}.html`;
      const { data: html } = await axios.get<string>(url, {
        headers: cookie ? { ...PAGE_HEADERS, cookie } : PAGE_HEADERS,
        timeout: REQUEST_TIMEOUT,
      });

      const $ = cheerio.load(html);
      const items: MusicItem[] = [];
      const seen = new Set<string>();

      $('.play_list ul li').each((_, el) => {
        const anchor = $(el).find('.name a').first();
        const href = cleanText(anchor.attr('href'));
        const rawTitle = cleanText(anchor.text());
        if (!href || !rawTitle) return;

        const songId = extractSongId(href);
        if (!songId || seen.has(songId)) return;
        seen.add(songId);

        let title = rawTitle;
        let artist = cleanText(
          $(el).find('.singer, .artist, .zz, .lzz, .playzz, .author').first().text()
        );

        if (!artist) {
          const match = rawTitle.match(/^(.*?)\s*-\s*(.+)$/);
          if (match) {
            title = cleanText(match[1]);
            artist = cleanText(match[2]);
          }
        }

        items.push({
          id: songId,
          title: title || rawTitle,
          artist: artist || '未知歌手',
          provider: this.name,
          extra: {
            songUrl: absoluteUrl(href),
          },
        });
      });

      return items;
    } catch (error) {
      console.error('Aiting search error:', error);
      return [];
    }
  }

  async getPlayInfo(id: string): Promise<PlayInfo> {
    try {
      const cookie = await this.bootstrapCookie();
      const songUrl = `${BASE_URL}/song/${encodeURIComponent(id)}.html`;

      const { data: html } = await axios.get<string>(songUrl, {
        headers: cookie ? { ...PAGE_HEADERS, cookie } : PAGE_HEADERS,
        timeout: REQUEST_TIMEOUT,
      });

      const $ = cheerio.load(html);
      const cover =
        absoluteUrl($('#mcover').attr('src')) ||
        absoluteUrl($('meta[property="og:image"]').attr('content'));

      const params = new URLSearchParams({
        id,
        type: 'music',
      });

      const { data } = await axios.post(`${BASE_URL}/js/play.php`, params, {
        headers: {
          'accept': 'application/json, text/javascript, */*; q=0.01',
          'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
          'origin': BASE_URL,
          'referer': songUrl,
          'user-agent': PAGE_HEADERS['user-agent'],
          'x-requested-with': 'XMLHttpRequest',
          ...(cookie ? { cookie } : {}),
        },
        timeout: REQUEST_TIMEOUT,
      });

      const payload = safeJson(data);
      const playUrl = String(payload.url || '').trim();
      if (!playUrl.startsWith('http')) {
        throw new Error(String(payload.msg || 'Invalid play url'));
      }

      const playCover = absoluteUrl(typeof payload.pic === 'string' ? payload.pic : undefined);

      return {
        url: playUrl,
        type: extractExt(playUrl),
        cover: playCover || cover,
      };
    } catch (error) {
      console.error('Aiting getPlayInfo error:', error);
      throw error;
    }
  }
}
