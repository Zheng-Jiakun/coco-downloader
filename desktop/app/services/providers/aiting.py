# coding: utf-8
import logging
import re
from http.cookies import SimpleCookie
from typing import Any

from bs4 import BeautifulSoup
from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import absolute_url, clean_text, extract_ext, is_http_url, quote_id, safe_json_loads

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.2t58.com"
REQUEST_TIMEOUT = 20

PAGE_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "cache-control": "max-age=0",
    "origin": BASE_URL,
    "priority": "u=0, i",
    "referer": f"{BASE_URL}/",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
}


def _extract_song_id(value: str) -> str:
    match = re.search(r"/song/([^/?#]+)\.html", value, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return value.strip("/").removesuffix(".html")


def _parse_cookie(headers: Any) -> str:
    cookie = SimpleCookie()
    raw_values = headers.get("set-cookie", "") if hasattr(headers, "get") else ""
    if not raw_values:
        return ""
    cookie.load(raw_values)
    return "; ".join(f"{key}={morsel.value}" for key, morsel in cookie.items())


class AitingProvider(MusicProvider):
    name = "aiting"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            cookie = self._bootstrap_cookie()
            html = self._http.get_text(
                f"{BASE_URL}/so/{quote_id(query.strip())}.html",
                headers=self._page_headers(cookie),
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException:
            LOGGER.exception("Aiting search error")
            return []
        return self._parse_search_html(html)

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        cookie = self._bootstrap_cookie()
        song_url = f"{BASE_URL}/song/{quote_id(song_id)}.html"
        html = self._http.get_text(song_url, headers=self._page_headers(cookie), timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(html, "html.parser")
        cover = self._extract_page_cover(soup)

        data = self._http.post_text(
            f"{BASE_URL}/js/play.php",
            headers=self._play_headers(song_url, cookie),
            data={"id": song_id, "type": "music"},
            timeout=REQUEST_TIMEOUT,
        )
        payload = safe_json_loads(data)
        play_url = clean_text(str(payload.get("url", ""))) if isinstance(payload, dict) else ""
        if not is_http_url(play_url):
            message = payload.get("msg", "Invalid play url") if isinstance(payload, dict) else "Invalid play url"
            raise ValueError(str(message))

        play_cover = None
        if isinstance(payload, dict) and isinstance(payload.get("pic"), str):
            play_cover = absolute_url(payload["pic"], f"{BASE_URL}/")
        return PlayInfo(
            url=play_url,
            type=extract_ext(play_url),
            cover=play_cover or cover,
        )

    def _bootstrap_cookie(self) -> str:
        try:
            response = self._http.get_response(f"{BASE_URL}/", headers=PAGE_HEADERS, timeout=REQUEST_TIMEOUT)
        except RequestException:
            return ""
        return _parse_cookie(response.headers)

    def _page_headers(self, cookie: str) -> dict[str, str]:
        if not cookie:
            return PAGE_HEADERS
        return {**PAGE_HEADERS, "cookie": cookie}

    def _play_headers(self, song_url: str, cookie: str) -> dict[str, str]:
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": BASE_URL,
            "referer": song_url,
            "user-agent": PAGE_HEADERS["user-agent"],
            "x-requested-with": "XMLHttpRequest",
        }
        if cookie:
            headers["cookie"] = cookie
        return headers

    def _parse_search_html(self, html: str) -> list[MusicItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[MusicItem] = []
        seen: set[str] = set()
        for element in soup.select(".play_list ul li"):
            item = self._parse_search_item(element)
            if not item or item.id in seen:
                continue
            seen.add(item.id)
            items.append(item)
        return items

    def _parse_search_item(self, element) -> MusicItem | None:
        anchor = element.select_one(".name a")
        href = clean_text(anchor.get("href") if anchor else "")
        raw_title = clean_text(anchor.get_text() if anchor else "")
        if not href or not raw_title:
            return None

        song_id = _extract_song_id(href)
        if not song_id:
            return None

        title, artist = self._parse_title_artist(element, raw_title)
        return MusicItem(
            id=song_id,
            title=title or raw_title,
            artist=artist or "未知歌手",
            provider=self.name,
            extra={"songUrl": absolute_url(href, f"{BASE_URL}/")},
        )

    def _parse_title_artist(self, element, raw_title: str) -> tuple[str, str]:
        artist_element = element.select_one(".singer, .artist, .zz, .lzz, .playzz, .author")
        artist = clean_text(artist_element.get_text() if artist_element else "")
        if artist:
            return raw_title, artist

        match = re.match(r"^(.*?)\s*-\s*(.+)$", raw_title)
        if not match:
            return raw_title, ""
        return clean_text(match.group(1)), clean_text(match.group(2))

    def _extract_page_cover(self, soup: BeautifulSoup) -> str | None:
        cover = soup.select_one("#mcover")
        if cover and cover.get("src"):
            return absolute_url(cover.get("src"), f"{BASE_URL}/")
        meta_cover = soup.select_one("meta[property='og:image']")
        if meta_cover and meta_cover.get("content"):
            return absolute_url(meta_cover.get("content"), f"{BASE_URL}/")
        return None
