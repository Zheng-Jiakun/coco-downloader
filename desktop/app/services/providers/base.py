# coding: utf-8
from abc import ABC, abstractmethod
from typing import Any

from app.models.music import LyricData, MusicItem, PlayInfo


class MusicProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, limit: int = 20, offset: int = 0) -> list[MusicItem]:
        raise NotImplementedError

    @abstractmethod
    def get_play_info(self, song_id: str, extra: dict[str, Any] | None = None) -> PlayInfo:
        raise NotImplementedError

    def get_lyric(self, song_id: str, extra: dict[str, Any] | None = None) -> LyricData:
        raise NotImplementedError(f"{self.name} does not support lyrics")
