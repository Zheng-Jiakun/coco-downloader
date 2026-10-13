# coding: utf-8
from typing import Any

from PyQt5.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, QSize, QThread, QTimer, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel, QWidget
from qfluentwidgets import FluentIcon, TransparentToolButton, InfoBar, InfoBarPosition
from qfluentwidgets.components.widgets.acrylic_label import AcrylicBrush

from app.common.signal_bus import signalBus
from app.components.lyric_widget import LyricWidget
from app.components.play_bar import (
    CentralButtonGroup,
    DEFAULT_COVER,
    PlayBarSongInfo,
    PlayProgressBar,
    RightWidgetGroup,
)
from app.models.music import LyricData, MusicItem
from app.services.providers import get_provider
from app.services.thread_lifecycle import retain_thread


class LyricFetchThread(QThread):
    """Fetch lyrics without blocking the UI thread."""

    finishedWithLyric = pyqtSignal(object, object)
    failed = pyqtSignal(object)

    def __init__(self, item: MusicItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item

    def run(self) -> None:
        try:
            provider = get_provider(self.item.provider)
            lyric = provider.get_lyric(self.item.id, dict(self.item.extra))
            if not self.isInterruptionRequested():
                self.finishedWithLyric.emit(self.item, lyric)
        except Exception:
            if not self.isInterruptionRequested():
                self.failed.emit(self.item)


class PlayingSongPanel(QWidget):
    """Current song information panel in the playing page."""

    enterSignal = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cover_pixmap = QPixmap(DEFAULT_COVER)
        self.cover_label = QLabel(self)
        self.title_label = QLabel(self)
        self.artist_label = QLabel(self)
        self.album_label = QLabel(self)
        self._init_widget()

    def set_song(self, item: MusicItem | None, cover: QPixmap | None = None) -> None:
        if item is None:
            self.title_label.setText(self.tr("未在播放"))
            self.artist_label.clear()
            self.album_label.clear()
            self._set_cover(QPixmap(DEFAULT_COVER))
            return

        self.title_label.setText(item.title)
        self.artist_label.setText(item.artist)
        self.album_label.setText(item.album or self.tr("未知专辑"))
        if cover is not None and not cover.isNull():
            self._set_cover(cover)
        else:
            self._set_cover(QPixmap(item.cover or DEFAULT_COVER))

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.enterSignal.emit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        side = min(320, max(180, self.width() - 24))
        x = (self.width() - side) // 2
        self.cover_label.setGeometry(x, 0, side, side)
        y = side + 28
        self.title_label.setGeometry(0, y, self.width(), 44)
        self.artist_label.setGeometry(0, y + 52, self.width(), 30)
        self.album_label.setGeometry(0, y + 88, self.width(), 28)
        self._set_cover(self.cover_pixmap)

    def _init_widget(self) -> None:
        self.setAttribute(Qt.WA_TranslucentBackground)
        for label in (self.title_label, self.artist_label, self.album_label):
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: white; background: transparent;")

        title_font = QFont("Microsoft YaHei UI")
        title_font.setPixelSize(28)
        title_font.setWeight(QFont.DemiBold)
        self.title_label.setFont(title_font)

        sub_font = QFont("Microsoft YaHei UI")
        sub_font.setPixelSize(18)
        self.artist_label.setFont(sub_font)
        self.album_label.setFont(sub_font)
        self.artist_label.setStyleSheet("color: rgba(255,255,255,190); background: transparent;")
        self.album_label.setStyleSheet("color: rgba(255,255,255,145); background: transparent;")
        self._set_cover(QPixmap(DEFAULT_COVER))

    def _set_cover(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            pixmap = QPixmap(DEFAULT_COVER)
        self.cover_pixmap = pixmap
        if self.cover_label.width() <= 0 or self.cover_label.height() <= 0:
            return
        self.cover_label.setPixmap(pixmap.scaled(
            self.cover_label.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        ))


class BlurCoverBackground(QWidget):
    """Blurred album cover background."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cover_pixmap = QPixmap(DEFAULT_COVER)
        self.acrylic_brush = AcrylicBrush(
            self,
            blurRadius=54,
            tintColor=QColor(20, 24, 28, 74),
            luminosityColor=QColor(12, 16, 20, 82),
            noiseOpacity=0.035,
        )
        self._init_widget()

    def set_cover(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            pixmap = QPixmap(DEFAULT_COVER)
        self.cover_pixmap = pixmap
        self._sync_brush()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_brush()

    def paintEvent(self, event) -> None:
        if self.acrylic_brush.isAvailable() and not self.acrylic_brush.image.isNull():
            self.acrylic_brush.paint()
            painter = QPainter(self)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 92))
            return

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(18, 21, 24))
        if not self.cover_pixmap.isNull():
            painter.drawPixmap(0, 0, self.cover_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            ))
        painter.fillRect(self.rect(), QColor(0, 0, 0, 118))

    def _init_widget(self) -> None:
        self.setAttribute(Qt.WA_StyledBackground)
        self._sync_brush()

    def _sync_brush(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return

        self.acrylic_brush.setBlurPicSize(self.size())
        self.acrylic_brush.setImage(self.cover_pixmap)
        self.update()


class PlayingPagePlayBar(QWidget):
    """Transparent compact controls used only on the playing page."""

    playPauseRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    modeChanged = pyqtSignal(object)
    volumeChanged = pyqtSignal(int)
    muteRequested = pyqtSignal()
    positionChanged = pyqtSignal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.central_group = CentralButtonGroup(self)
        self.progress_bar = PlayProgressBar(0, self)
        self.right_group = RightWidgetGroup(self)
        self.setFixedHeight(122)
        self._init_widget()
        self._connect_signals()

    def set_song(self, song: PlayBarSongInfo) -> None:
        self.progress_bar.set_total_time(song.duration)

    def set_playing(self, playing: bool) -> None:
        self.central_group.play_button.set_playing(playing)

    def set_position(self, position: int) -> None:
        self.progress_bar.set_current_time(position)

    def set_volume(self, volume: int) -> None:
        self.right_group.volume_slider.blockSignals(True)
        self.right_group.volume_slider.setValue(volume)
        self.right_group.volume_slider.blockSignals(False)
        self.right_group.volume_button.set_volume(volume)

    def set_muted(self, muted: bool) -> None:
        self.right_group.volume_button.set_muted(muted)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._adjust_widgets()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 42))

    def _init_widget(self) -> None:
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.progress_bar.resize(min(640, max(420, self.width() - 420)), self.progress_bar.height())

    def _adjust_widgets(self) -> None:
        width = self.width()
        progress_width = min(720, max(420, width - 520))
        self.progress_bar.resize(progress_width, self.progress_bar.height())
        self.central_group.move((width - self.central_group.width()) // 2, 4)
        self.progress_bar.move((width - self.progress_bar.width()) // 2, 82)
        self.right_group.move(width - self.right_group.width() - 22, 8)

    def _connect_signals(self) -> None:
        self.central_group.play_button.clicked.connect(self.playPauseRequested)
        self.central_group.previous_button.clicked.connect(self.previousRequested)
        self.central_group.next_button.clicked.connect(self.nextRequested)
        self.central_group.mode_button.modeChanged.connect(self.modeChanged)
        self.right_group.volume_button.clicked.connect(self.muteRequested)
        self.right_group.volume_slider.valueChanged.connect(self.volumeChanged)
        self.progress_bar.slider.clicked.connect(self.positionChanged)
        self.progress_bar.slider.sliderMoved.connect(self.positionChanged)


class PlayingInterface(QWidget):
    """Full playing page with cover, lyrics and an auto-hiding play bar."""

    exitRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_item: MusicItem | None = None
        self.current_index = -1
        self.cover_pixmap = QPixmap(DEFAULT_COVER)
        self.lyric_thread: LyricFetchThread | None = None
        self.is_play_bar_visible = False

        self.background = BlurCoverBackground(self)
        self.back_button = TransparentToolButton(FluentIcon.ARROW_DOWN.icon(color=Qt.white), self)
        self.song_panel = PlayingSongPanel(self)
        self.lyric_widget = LyricWidget(self)
        self.play_bar = PlayingPagePlayBar(self)
        self.hide_bar_timer = QTimer(self)
        self.play_bar_animation = QPropertyAnimation(self.play_bar, b"pos", self)

        self._init_widget()
        self._connect_signals()

    def set_song(self, item: MusicItem, index: int) -> None:
        self.current_item = item
        self.current_index = index
        self.song_panel.set_song(item, self.cover_pixmap)
        self.play_bar.set_song(self._to_play_bar_song(item))
        self.lyric_widget.set_loading(True)
        self._fetch_lyric(item)

    def set_cover(self, pixmap: QPixmap, color: Any = None) -> None:
        if pixmap.isNull():
            return
        self.cover_pixmap = pixmap
        self.background.set_cover(pixmap)
        self.song_panel.set_song(self.current_item, pixmap)
        self.update()

    def set_position(self, position: int) -> None:
        self.play_bar.set_position(position)
        self.lyric_widget.set_position(position)

    def set_duration(self, duration: int) -> None:
        self.play_bar.progress_bar.set_total_time(duration // 1000)

    def set_playing(self, playing: bool) -> None:
        self.play_bar.set_playing(playing)

    def show_play_bar(self) -> None:
        self.is_play_bar_visible = True
        self.play_bar_animation.stop()
        self._prepare_play_bar_animation(self._visible_play_bar_pos())
        self.play_bar.show()
        self.play_bar.raise_()
        self.play_bar_animation.start()
        self.hide_bar_timer.start()

    def hide_play_bar(self) -> None:
        if not self.is_play_bar_visible:
            return
        self.is_play_bar_visible = False
        self.hide_bar_timer.stop()
        self.play_bar_animation.stop()
        self._prepare_play_bar_animation(self._hidden_play_bar_pos())
        self.play_bar_animation.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.show_play_bar()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self.show_play_bar()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.background.setGeometry(self.rect())
        self.background.lower()
        self.back_button.move(22, 30)
        self.play_bar.resize(self.width(), self.play_bar.height())
        self._place_play_bar()

        left_width = min(420, max(320, self.width() // 3))
        self.song_panel.setGeometry(64, max(112, self.height() // 2 - 250), left_width, 460)
        lyric_x = left_width + 116
        self.lyric_widget.setGeometry(lyric_x, 76, max(300, self.width() - lyric_x - 56), self.height() - 158)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 30))

    def _init_widget(self) -> None:
        self.setObjectName("playingInterface")
        self.setAttribute(Qt.WA_StyledBackground)
        self.setMouseTracking(True)
        self.back_button.setFixedSize(44, 44)
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setStyleSheet(
            "TransparentToolButton{border-radius:22px;background:rgba(255,255,255,18);}"
            "TransparentToolButton:hover{background:rgba(255,255,255,32);}"
            "TransparentToolButton:pressed{background:rgba(255,255,255,44);}"
        )
        self.play_bar.setMouseTracking(True)
        self.play_bar.installEventFilter(self)
        self.play_bar.hide()
        self.hide_bar_timer.setInterval(3000)
        self.play_bar_animation.setDuration(260)
        self.play_bar_animation.setEasingCurve(QEasingCurve.OutCubic)

    def _connect_signals(self) -> None:
        self.back_button.clicked.connect(self.exitRequested)
        self.song_panel.enterSignal.connect(self.show_play_bar)
        self.play_bar.playPauseRequested.connect(signalBus.playbackToggleRequested)
        self.play_bar.previousRequested.connect(signalBus.playbackPreviousRequested)
        self.play_bar.nextRequested.connect(signalBus.playbackNextRequested)
        self.play_bar.positionChanged.connect(signalBus.playbackSeekRequested)
        self.play_bar.volumeChanged.connect(signalBus.playbackVolumeChanged)
        self.play_bar.muteRequested.connect(signalBus.playbackMuteRequested)
        self.play_bar.modeChanged.connect(signalBus.playbackModeChanged)
        self.hide_bar_timer.timeout.connect(self.hide_play_bar)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.play_bar and event.type() in (QEvent.Enter, QEvent.MouseMove):
            self.show_play_bar()
        return super().eventFilter(watched, event)

    def _place_play_bar(self) -> None:
        if self.is_play_bar_visible:
            self.play_bar.move(self._visible_play_bar_pos())
        else:
            self.play_bar.move(self._hidden_play_bar_pos())

    def _visible_play_bar_pos(self) -> QPoint:
        return QPoint(0, self.height() - self.play_bar.height())

    def _hidden_play_bar_pos(self) -> QPoint:
        return QPoint(0, self.height())

    def _prepare_play_bar_animation(self, end_pos: QPoint) -> None:
        self.play_bar_animation.setStartValue(self.play_bar.pos())
        self.play_bar_animation.setEndValue(end_pos)
        try:
            self.play_bar_animation.finished.disconnect()
        except TypeError:
            pass
        if end_pos == self._hidden_play_bar_pos():
            self.play_bar_animation.finished.connect(self.play_bar.hide)

    def _fetch_lyric(self, item: MusicItem) -> None:
        if self._is_lyric_thread_running():
            self.lyric_thread.requestInterruption()

        thread = LyricFetchThread(item, self)
        thread.finishedWithLyric.connect(self._on_lyric_loaded)
        thread.failed.connect(self._on_lyric_failed)
        thread.finished.connect(lambda: self._clear_lyric_thread(thread))
        retain_thread(thread)
        self.lyric_thread = thread
        thread.start()

    def _is_lyric_thread_running(self) -> bool:
        if self.lyric_thread is None:
            return False
        try:
            return self.lyric_thread.isRunning()
        except RuntimeError:
            self.lyric_thread = None
            return False

    def _clear_lyric_thread(self, thread: LyricFetchThread) -> None:
        if self.lyric_thread is thread:
            self.lyric_thread = None

    def _on_lyric_loaded(self, item: MusicItem, lyric: LyricData) -> None:
        if self.current_item is None or item.id != self.current_item.id or item.provider != self.current_item.provider:
            return
        self.lyric_widget.set_lyric(lyric)

    def _on_lyric_failed(self, item: MusicItem) -> None:
        if self.current_item is None or item.id != self.current_item.id or item.provider != self.current_item.provider:
            return
        self.lyric_widget.set_lyric(None)
        InfoBar.warning(title=self.tr("歌词加载失败"), content=self.tr("第三方渠道未能提供歌词，不影响歌曲播放。"),
                        duration=4000, position=InfoBarPosition.TOP, parent=self.window())

    def _to_play_bar_song(self, item: MusicItem) -> PlayBarSongInfo:
        return PlayBarSongInfo(
            title=item.title,
            singer=item.artist,
            album=item.album or self.tr("未知专辑"),
            duration=0,
            cover=item.cover or DEFAULT_COVER,
        )
