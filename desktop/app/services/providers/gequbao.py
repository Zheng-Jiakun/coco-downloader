# coding: utf-8
import json
import logging
import re
from typing import Any

from bs4 import BeautifulSoup
from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import clean_text, decode_js_string_literal, extract_ext, is_http_url, quote_id

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15

HEADERS_PAGE = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "cache-control": "max-age=0",
    "priority": "u=0, i",
    "referer": "https://www.gequbao.com/",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

HEADERS_API = {
    "accept": "application/json, text/javascript, */*; q=0.01",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "origin": "https://www.gequbao.com",
    "priority": "u=1, i",
    "sec-ch-ua": HEADERS_PAGE["sec-ch-ua"],
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": HEADERS_PAGE["user-agent"],
    "x-requested-with": "XMLHttpRequest",
}


def _extract_app_data(html: str) -> dict[str, Any]:
    json_parse_match = re.search(
        r"window\.appData\s*=\s*JSON\.parse\((['\"])([\s\S]*?)\1\)\s*;",
        html,
    )
    if json_parse_match:
        try:
            return json.loads(decode_js_string_literal(json_parse_match.group(2)))
        except (json.JSONDecodeError, ValueError):
            return {}

    json_object_match = re.search(r"window\.appData\s*=\s*(\{[\s\S]*?\})\s*;", html)
    if not json_object_match:
        return {}

    try:
        return json.loads(json_object_match.group(1))
    except json.JSONDecodeError:
        return {}


def _split_title_artist(title: str) -> tuple[str, str]:
    if " - " in title:
        parts = [part.strip() for part in title.split(" - ", 1)]
        if len(parts) == 2:
            return parts[0], parts[1]
    if "-" in title:
        parts = [part.strip() for part in title.split("-", 1)]
        if len(parts) == 2:
            return parts[0], parts[1]
    return title, ""


def _parse_artist(anchor, title: str) -> str:
    parent = anchor.find_parent(["li", "div", "tr"])
    if parent:
        artist_anchor = parent.select_one("a[href*='/singer/'], a[href*='/artist/']")
        if artist_anchor:
            return clean_text(artist_anchor.get_text())

        parent_text = clean_text(parent.get_text())
        if " - " in parent_text:
            parts = [part.strip() for part in parent_text.split(" - ") if part.strip()]
            if len(parts) >= 2 and title in parts[0]:
                return parts[1]

    _, artist = _split_title_artist(title)
    return artist


def _build_item(song_id: str, title: str, artist: str) -> MusicItem:
    item_title = title
    if artist:
        for separator in (f" - {artist}", f"-{artist}"):
            if separator in item_title:
                item_title = item_title.replace(separator, "").strip()
                break

    return MusicItem(
        id=song_id,
        title=item_title,
        artist=artist or "未知歌手",
        provider="gequbao",
    )


class GequbaoProvider(MusicProvider):
    name = "gequbao"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            html = self._http.get_text(
                f"https://www.gequbao.com/s/{quote_id(query)}",
                headers=HEADERS_PAGE,
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException:
            LOGGER.exception("Gequbao search error")
            return []

        return self._parse_search_html(html)

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        page_url = f"https://www.gequbao.com/music/{song_id}"
        html = self._http.get_text(
            page_url,
            headers={**HEADERS_PAGE, "referer": "https://www.gequbao.com/"},
            timeout=REQUEST_TIMEOUT,
        )
        app_data = _extract_app_data(html)
        play_id = app_data.get("play_id") if isinstance(app_data.get("play_id"), str) else ""
        cover = app_data.get("mp3_cover") if isinstance(app_data.get("mp3_cover"), str) else None
        if not play_id:
            raise ValueError("Failed to extract play_id")

        api_data = self._http.post_json(
            "https://www.gequbao.com/api/play-url",
            headers={**HEADERS_API, "referer": page_url},
            data={"id": play_id},
            timeout=REQUEST_TIMEOUT,
        )
        payload = api_data.get("data", {}) if isinstance(api_data, dict) else {}
        url = clean_text(str(payload.get("url", "")))
        if api_data.get("code") != 1 or not is_http_url(url):
            raise ValueError(str(api_data.get("msg", "API error")))

        return PlayInfo(url=url, type=extract_ext(url), cover=cover)

    def _parse_search_html(self, html: str) -> list[MusicItem]:
        soup = BeautifulSoup(html, "html.parser")
        items: list[MusicItem] = []
        seen: set[str] = set()

        for anchor in soup.select("a[href^='/music/']"):
            item = self._parse_anchor(anchor)
            if not item:
                continue
            key = f"{item.id}-{item.title}"
            if key in seen:
                continue
            seen.add(key)
            items.append(item)

        return items

    def _parse_anchor(self, anchor) -> MusicItem | None:
        href = anchor.get("href", "")
        match = re.search(r"/music/([0-9]+)", href)
        if not match:
            return None

        title = clean_text(anchor.get_text())
        if not title or title in {"播放&下载", "播放", "下载"}:
            return None
        if title.startswith("网友刚刚下载了"):
            return None

        artist = _parse_artist(anchor, title)
        return _build_item(match.group(1), title, artist)
