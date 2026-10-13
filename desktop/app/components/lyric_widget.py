# coding: utf-8
import bisect
from dataclasses import dataclass

from PyQt5.QtCore import QPropertyAnimation, Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QLabel, QScrollArea, QVBoxLayout, QWidget

from app.models.music import LyricData


@dataclass(frozen=True)
class DisplayLyricLine:
    time: float
    text: str


class LyricLineLabel(QLabel):
    """Centered lyric line."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setText(text)
        self.set_playing(False)

    def set_playing(self, is_playing: bool) -> None:
        font = QFont("Microsoft YaHei UI")
        font.setPixelSize(28 if is_playing else 22)
        font.setWeight(QFont.DemiBold if is_playing else QFont.Normal)
        self.setFont(font)

        color = "rgb(255, 255, 255)" if is_playing else "rgb(185, 185, 185)"
        self.setStyleSheet(f"color: {color}; background: transparent;")
        self.adjustSize()


class LyricWidget(QScrollArea):
    """Scrollable lyric panel without visible scroll bars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.lines: list[DisplayLyricLine] = []
        self.labels: list[LyricLineLabel] = []
        self.current_index = -1
        self.scroll_widget = QWidget(self)
        self.layout = QVBoxLayout(self.scroll_widget)
        self.loading_label = QLabel(self.tr("正在加载歌词..."), self)
        self.scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value", self)

        self._init_widget()

    def set_loading(self, loading: bool) -> None:
        self.loading_label.setVisible(loading)
        self.scroll_widget.setVisible(not loading)

    def set_lyric(self, lyric: LyricData | None) -> None:
        self.scroll_animation.stop()
        self.current_index = -1
        self.lines = self._to_display_lines(lyric)
        self._rebuild_labels()
        self.verticalScrollBar().setValue(0)
        self.set_loading(False)

    def set_position(self, position: int) -> None:
        if not self.lines:
            return

        seconds = position / 1000
        times = [line.time for line in self.lines]
        index = bisect.bisect_right(times, seconds) - 1
        index = max(0, min(index, len(self.lines) - 1))
        if index == self.current_index:
            return

        if 0 <= self.current_index < len(self.labels):
            self.labels[self.current_index].set_playing(False)
        self.current_index = index
        self.labels[index].set_playing(True)
        self._scroll_to_label(self.labels[index])

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.scroll_widget.setFixedWidth(self.width())
        self.loading_label.adjustSize()
        self.loading_label.move(
            (self.width() - self.loading_label.width()) // 2,
            max(80, self.height() // 3),
        )

    def _init_widget(self) -> None:
        self.setWidget(self.scroll_widget)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea, QWidget { background: transparent; }")

        self.layout.setContentsMargins(40, 160, 40, 160)
        self.layout.setSpacing(34)
        self.loading_label.setStyleSheet("color: rgba(255,255,255,170); font-size: 22px; background: transparent;")
        self.loading_label.hide()

        self.scroll_animation.setDuration(350)

    def _to_display_lines(self, lyric: LyricData | None) -> list[DisplayLyricLine]:
        if lyric is None or not lyric.lines:
            return [DisplayLyricLine(0, self.tr("暂无歌词"))]
        return [DisplayLyricLine(line.time, line.text) for line in lyric.lines if line.text]

    def _rebuild_labels(self) -> None:
        while self.labels:
            label = self.labels.pop()
            self.layout.removeWidget(label)
            label.deleteLater()

        for line in self.lines:
            label = LyricLineLabel(line.text, self.scroll_widget)
            self.labels.append(label)
            self.layout.addWidget(label, 0, Qt.AlignHCenter)
        QApplication.processEvents()
        self.scroll_widget.adjustSize()

    def _scroll_to_label(self, label: QLabel) -> None:
        target = label.y() - self.height() // 2 + label.height() // 2
        target = max(0, target)
        self.scroll_animation.setStartValue(self.verticalScrollBar().value())
        self.scroll_animation.setEndValue(target)
        self.scroll_animation.start()
