# coding: utf-8
import logging
from typing import Any
from urllib.parse import urlencode

from requests import RequestException

from app.models.music import MusicItem, PlayInfo
from app.services.errors import ProviderNetworkError

from .base import MusicProvider
from .http_client import ProviderHttpClient
from .utils import validate_audio_url

LOGGER = logging.getLogger(__name__)
REQUEST_TIMEOUT = 15

SEARCH_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "activityid": "v4_zt_2022_music",
    "appid": "ce",
    "channel": "014X031",
    "connection": "keep-alive",
    "deviceid": "E60C6B2F-7F11-4362-9FCE-6F1CC86E0F18",
    "host": "c.musicapp.migu.cn",
    "hwid": "",
    "imei": "",
    "h5page": "",
    "imsi": "",
    "location-info": "",
    "mgm-user-agent": "",
    "oaid": "",
    "uid": "",
    "location-data": "",
    "logid": "h5page[1808]",
    "mgm-network-operators": "02",
    "mgm-network-standard": "03",
    "mgm-network-type": "03",
    "origin": "https://y.migu.cn",
    "recommendstatus": "1",
    "referer": "https://y.migu.cn/app/v4/zt/2022/music/index.html",
    "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "subchannel": "014X031",
    "test": "00",
    "ua": "Android_migu",
    "version": "6.8.8",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
}

MUSIC_QUALITIES = {
    "LQ": "mp3",
    "PQ": "mp3",
    "HQ": "mp3",
    "SQ": "flac",
    "ZQ": "flac",
    "Z3D": "flac",
    "ZQ24": "flac",
    "ZQ32": "flac",
}


def _parse_size(value: Any) -> float:
    raw_value = str(value or "").replace("MB", "").strip()
    try:
        return float(raw_value)
    except ValueError:
        return 0


def _build_search_url(keyword: str, page_no: int = 1, page_size: int = 20) -> str:
    search_switch = "{'song': 1, 'album': 0, 'singer': 0, 'tagSong': 1, 'mvSong': 0, 'bestShow': 1}"
    query = urlencode(
        {
            "text": keyword,
            "pageNo": str(page_no),
            "pageSize": str(page_size),
            "isCopyright": "1",
            "sort": "1",
            "searchSwitch": search_switch,
        }
    )
    return f"https://c.musicapp.migu.cn/v1.0/content/search_all.do?{query}"


def _build_listen_url(content_id: str, copyright_id: str, resource_type: str, tone_flag: str) -> str:
    return (
        "https://c.musicapp.migu.cn/MIGUM3.0/strategy/listen-url/v2.4"
        f"?resourceType={resource_type}"
        "&netType=01"
        "&scene="
        f"&toneFlag={tone_flag}"
        f"&contentId={content_id}"
        f"&copyrightId={copyright_id}"
        f"&lowerQualityContentId={content_id}"
    )


def _fallback_url(content_id: str, copyright_id: str, tone_flag: str, resource_type: str) -> str:
    return (
        "https://app.pd.nf.migu.cn/MIGUM3.0/v1.0/content/sub/listenSong.do"
        f"?channel=mx&copyrightId={copyright_id}"
        f"&contentId={content_id}"
        f"&toneFlag={tone_flag}"
        f"&resourceType={resource_type}"
        "&userId=15548614588710179085069"
        "&netType=00"
    )


def _build_id(content_id: str | None, copyright_id: str | None) -> str:
    if not content_id or not copyright_id:
        return ""
    return f"{content_id}_{copyright_id}"


def _parse_id(song_id: str) -> tuple[str, str]:
    parts = song_id.split("_", 1)
    if len(parts) != 2:
        return "", ""
    return parts[0], parts[1]


def _join_names(items: list[Any]) -> str:
    names = []
    for item in items:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return ", ".join(names)


class MiguProvider(MusicProvider):
    name = "migu"

    def __init__(self) -> None:
        self._http = ProviderHttpClient()

    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        try:
            data = self._http.get_json(_build_search_url(query), headers=SEARCH_HEADERS, timeout=REQUEST_TIMEOUT)
        except RequestException:
            LOGGER.exception("Migu search error")
            return []

        items = self._extract_song_list(data)
        return [item for item in (self._map_item(raw_item) for raw_item in items) if item]

    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        content_id, copyright_id = _parse_id(song_id)
        if not content_id or not copyright_id:
            raise ValueError("Invalid id")

        song = extra.get("song") if extra and isinstance(extra.get("song"), dict) else self._find_song(content_id)
        if not song:
            raise ValueError("Song not found")

        rate_formats = self._get_rate_formats(song)
        for rate in rate_formats:
            play_info = self._try_rate(content_id, copyright_id, rate)
            if play_info:
                return play_info
        raise ValueError("咪咕未返回可用音频，该歌曲可能暂不可用，请尝试其他歌曲或音源")

    def _extract_song_list(self, data: Any) -> list[Any]:
        if not isinstance(data, dict):
            return []
        song_data = data.get("songResultData", {})
        result = song_data.get("result", []) if isinstance(song_data, dict) else []
        return result if isinstance(result, list) else []

    def _map_item(self, item: Any) -> MusicItem | None:
        if not isinstance(item, dict):
            return None
        song_id = _build_id(item.get("contentId"), item.get("copyrightId"))
        if not song_id:
            return None
        cover_items = item.get("imgItems", [])
        cover = cover_items[-1].get("img") if isinstance(cover_items, list) and cover_items else None
        return MusicItem(
            id=song_id,
            title=item.get("name") or "未知歌曲",
            artist=_join_names(item.get("singers", [])) or "未知歌手",
            album=_join_names(item.get("albums", [])) or None,
            cover=cover,
            provider=self.name,
            extra={"song": item},
        )

    def _find_song(self, content_id: str) -> dict[str, Any] | None:
        data = self._http.get_json(
            _build_search_url(content_id, 1, 1),
            headers=SEARCH_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        items = self._extract_song_list(data)
        for item in items:
            if isinstance(item, dict) and item.get("contentId") == content_id:
                return item
        return None

    def _get_rate_formats(self, song: dict[str, Any]) -> list[dict[str, Any]]:
        rates = song.get("rateFormats", []) + song.get("newRateFormats", [])
        valid_rates = [
            rate
            for rate in rates
            if isinstance(rate, dict) and rate.get("formatType") and rate.get("resourceType")
        ]
        unique_rates = {(str(rate["formatType"]), str(rate["resourceType"])): rate for rate in valid_rates}
        return sorted(
            unique_rates.values(),
            key=lambda rate: _parse_size(rate.get("size") or rate.get("iosSize") or rate.get("androidSize")),
            reverse=True,
        )

    def _try_rate(self, content_id: str, copyright_id: str, rate: dict[str, Any]) -> PlayInfo | None:
        resource_type = str(rate["resourceType"])
        tone_flag = str(rate["formatType"])
        try:
            data = self._http.get_json(
                _build_listen_url(content_id, copyright_id, resource_type, tone_flag),
                headers=SEARCH_HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
        except (ProviderNetworkError, RequestException, ValueError):
            data = {}

        payload = data.get("data", {}) if isinstance(data, dict) else {}
        url = payload.get("url") if isinstance(payload, dict) else None
        if not url:
            url = _fallback_url(content_id, copyright_id, tone_flag, resource_type)
        try:
            final_url = validate_audio_url(self._http, str(url), timeout=REQUEST_TIMEOUT)
        except (ProviderNetworkError, RequestException, ValueError):
            return None
        return PlayInfo(url=final_url, type=MUSIC_QUALITIES.get(tone_flag, "mp3"), bitrate=tone_flag)
