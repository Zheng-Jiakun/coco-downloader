# coding: utf-8
import logging
import time
from typing import Any

from requests import RequestException

from app.models.music import MusicItem, PlayInfo

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import extract_ext

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://music.wjhe.top"
REQUEST_TIMEOUT = 20
PLAYBACK_FORMAT_PRIORITY = ("mp3", "m4a", "aac")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Referer": f"{BASE_URL}/",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "sec-ch-ua": "\"Google Chrome\";v=\"149\", \"Chromium\";v=\"149\", \"Not)A;Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
}


def _seconds_to_hms(seconds: Any) -> str | None:
    if seconds is None:
        return None
    total = int(float(seconds))
    hour = total // 3600
    minute = total % 3600 // 60
    second = total % 60
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def _pick_best_file_link(file_links: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        item for item in file_links
        if isinstance(item, dict) and item.get("quality") is not None and item.get("format")
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: float(item.get("quality") or 0), reverse=True)[0]


def _pick_default_file_link(file_links: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        item for item in file_links
        if isinstance(item, dict) and item.get("quality") is not None and item.get("format")
    ]
    if not candidates:
        return None

    for file_format in PLAYBACK_FORMAT_PRIORITY:
        format_items = [
            item for item in candidates
            if str(item.get("format") or "").lower() == file_format
        ]
        if format_items:
            return sorted(format_items, key=lambda item: float(item.get("quality") or 0), reverse=True)[0]
    return _pick_best_file_link(file_links)


def _build_quality_options(file_links: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates = [
        item for item in file_links
        if isinstance(item, dict) and item.get("quality") is not None and item.get("format")
    ]
    sorted_items = sorted(candidates, key=lambda item: float(item.get("quality") or 0), reverse=True)
    return [
        {
            "value": f"{item['quality']}:{item['format']}",
            "label": f"{item['quality']} {item['format']}".upper(),
            "quality": str(item["quality"]),
            "format": str(item["format"]),
        }
        for item in sorted_items
    ]


class JooxProvider(MusicProvider):
    name = "joox"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            data = self._http.get_json(
                f"{BASE_URL}/api/music/joox/search",
                headers=HEADERS,
                params={
                    "key": query.strip(),
                    "pageIndex": "1",
                    "pageSize": "10",
                    "_": str(int(time.time() * 1000)),
                },
                timeout=REQUEST_TIMEOUT,
            )
        except RequestException:
            LOGGER.exception("Joox search error")
            return []

        payload = data.get("data", {}) if isinstance(data, dict) else {}
        items = payload.get("data", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            return []
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        preferred = self._get_preferred_file_link(extra)
        if not preferred:
            raise ValueError("Missing joox quality info")

        cover = self._resolve_url(song_id, "500", "jpg", 10)
        url = self._resolve_url(
            song_id,
            str(preferred["quality"]),
            str(preferred["format"]),
            REQUEST_TIMEOUT,
        )
        if not url.startswith("http"):
            raise ValueError("Invalid joox play url")

        return PlayInfo(
            url=url,
            type=extract_ext(url, str(preferred["format"]).lower()),
            cover=cover if cover.startswith("http") else None,
            bitrate=f"{preferred['quality']} {preferred['format']}".upper(),
        )

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict) or not item.get("ID"):
            return None
        file_links = item.get("fileLinks", [])
        if not isinstance(file_links, list) or not file_links:
            return None
        title = str(item.get("name") or item.get("title") or "").strip()
        if not title:
            return None

        best_link = _pick_default_file_link(file_links)
        artists = self._join_artist_names(item.get("singers", []))
        album = item.get("album", {})
        return MusicItem(
            id=str(item["ID"]),
            title=title,
            artist=artists or "未知歌手",
            album=album.get("name") if isinstance(album, dict) else None,
            duration=_seconds_to_hms(item.get("duration")),
            provider=self.name,
            extra={
                "source": "joox",
                "fileLinks": file_links,
                "selectedQuality": str(best_link["quality"]) if best_link else None,
                "selectedFormat": str(best_link["format"]) if best_link else None,
                "qualityOptions": _build_quality_options(file_links),
            },
        )

    def _get_preferred_file_link(self, extra: dict[str, Any] | None) -> dict[str, Any] | None:
        payload = extra or {}
        file_links = payload.get("fileLinks", [])
        if not isinstance(file_links, list):
            return None

        selected_quality = str(payload.get("selectedQuality") or "")
        selected_format = str(payload.get("selectedFormat") or "")
        for item in file_links:
            if not isinstance(item, dict):
                continue
            if str(item.get("quality") or "") == selected_quality and str(item.get("format") or "") == selected_format:
                return item
        return _pick_default_file_link(file_links)

    def _resolve_url(self, song_id: str, quality: str, file_format: str, timeout: int) -> str:
        return self._http.head_final_url(
            f"{BASE_URL}/api/music/joox/url",
            headers=HEADERS,
            params={"ID": song_id, "quality": quality, "format": file_format},
            timeout=timeout,
        )

    def _join_artist_names(self, singers: Any) -> str:
        if not isinstance(singers, list):
            return ""
        names = []
        for singer in singers:
            if isinstance(singer, dict) and singer.get("name"):
                names.append(str(singer["name"]).strip())
        return ", ".join(name for name in names if name)
