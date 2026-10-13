# coding: utf-8
from dataclasses import dataclass
from enum import Enum

from PyQt5.QtCore import QPoint, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap
from PyQt5.QtWidgets import QLabel, QProxyStyle, QSlider, QToolButton, QWidget
from qfluentwidgets import isDarkTheme

BAR_COLOR = QColor(42, 119, 159)
DARK_BAR_COLOR = QColor(32, 32, 32)
DEFAULT_COVER = ":/app/images/play_bar/album_200_200.png"


@dataclass(frozen=True)
class PlayBarSongInfo:
    title: str
    singer: str
    album: str
    duration: int
    cover: str = DEFAULT_COVER


class PlaybackMode(Enum):
    LIST_LOOP = "list_loop"
    RANDOM = "random"
    SINGLE_LOOP = "single_loop"


def _asset(name: str) -> str:
    return f":/app/images/play_bar/{name}"


def _format_time(seconds: int) -> str:
    return f"{seconds // 60}:{str(seconds % 60).rjust(2, '0')}"


def _font(pixel_size: int, weight: int = QFont.Normal) -> QFont:
    font = QFont("Segoe UI")
    font.setPixelSize(pixel_size)
    font.setWeight(weight)
    return font


class ClickableSlider(QSlider):
    clicked = pyqtSignal(int)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        super().mousePressEvent(event)
        if self.maximum() <= self.minimum():
            return

        value = int(event.pos().x() / max(self.width(), 1) * self.maximum())
        self.setValue(value)
        self.clicked.emit(self.value())


class HollowHandleStyle(QProxyStyle):
    """Groove's hollow white slider handle."""

    def __init__(self, config: dict[str, object] | None = None) -> None:
        super().__init__()
        self.config = {
            "groove.height": 3,
            "sub-page.color": QColor(255, 255, 255),
            "add-page.color": QColor(255, 255, 255, 64),
            "handle.color": QColor(255, 255, 255),
            "handle.ring-width": 4,
            "handle.hollow-radius": 6,
            "handle.margin": 4,
        }
        if config:
            self.config.update(config)
        self.config["handle.size"] = self._handle_size()

    def subControlRect(self, control, option, sub_control, widget=None):
        if control != self.CC_Slider or option.orientation != Qt.Horizontal:
            return super().subControlRect(control, option, sub_control, widget)
        if sub_control == self.SC_SliderTickmarks:
            return super().subControlRect(control, option, sub_control, widget)
        if sub_control == self.SC_SliderGroove:
            return self._groove_rect(option)
        if sub_control == self.SC_SliderHandle:
            return self._handle_rect(option)
        return super().subControlRect(control, option, sub_control, widget)

    def drawComplexControl(self, control, option, painter, widget=None) -> None:
        if control != self.CC_Slider or option.orientation != Qt.Horizontal:
            super().drawComplexControl(control, option, painter, widget)
            return

        groove_rect = self.subControlRect(control, option, self.SC_SliderGroove, widget)
        handle_rect = self.subControlRect(control, option, self.SC_SliderHandle, widget)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        self._draw_groove(painter, groove_rect, handle_rect)
        self._draw_handle(painter, option, handle_rect, widget)

    def _handle_size(self) -> QSize:
        margin = int(self.config["handle.margin"])
        ring_width = int(self.config["handle.ring-width"])
        hollow_radius = int(self.config["handle.hollow-radius"])
        width = margin + ring_width + hollow_radius
        return QSize(2 * width, 2 * width)

    def _groove_rect(self, option) -> QRectF:
        height = int(self.config["groove.height"])
        return QRectF(0, (option.rect.height() - height) // 2, option.rect.width(), height).toRect()

    def _handle_rect(self, option) -> QRectF:
        size = self.config["handle.size"]
        x = self.sliderPositionFromValue(
            option.minimum,
            option.maximum,
            option.sliderPosition,
            option.rect.width(),
        )
        x *= (option.rect.width() - size.width()) / max(option.rect.width(), 1)
        return QRectF(x, 0, size.width(), size.height()).toRect()

    def _draw_groove(self, painter: QPainter, groove_rect, handle_rect) -> None:
        painter.save()
        painter.translate(groove_rect.topLeft())
        crossed_width = handle_rect.x() - groove_rect.x()
        handle_width = self.config["handle.size"].width()
        painter.setBrush(self.config["sub-page.color"])
        painter.drawRect(0, 0, crossed_width, int(self.config["groove.height"]))
        painter.setBrush(self.config["add-page.color"])
        painter.drawRect(
            crossed_width + handle_width,
            0,
            groove_rect.width() - crossed_width,
            int(self.config["groove.height"]),
        )
        painter.restore()

    def _draw_handle(self, painter: QPainter, option, handle_rect, widget) -> None:
        ring_width = int(self.config["handle.ring-width"])
        hollow_radius = int(self.config["handle.hollow-radius"])
        radius = ring_width + hollow_radius
        center = handle_rect.center() + QPoint(1, 1)
        path = QPainterPath()
        path.addEllipse(center, radius, radius)
        path.addEllipse(center, hollow_radius, hollow_radius)

        handle_color = QColor(self.config["handle.color"])
        handle_color.setAlpha(153 if option.activeSubControls == self.SC_SliderHandle else 255)
        painter.setBrush(handle_color)
        painter.drawPath(path)
        if widget and widget.isSliderDown():
            handle_color.setAlpha(255)
            painter.setBrush(handle_color)
            painter.drawEllipse(handle_rect)


class TimeLabel(QLabel):
    def __init__(self, seconds: int, parent: QWidget | None = None) -> None:
        super().__init__(_format_time(seconds), parent)
        self.setFont(_font(15, QFont.Medium))
        self.setStyleSheet("color: white; background: transparent;")

    def set_time(self, seconds: int) -> None:
        self.setText(_format_time(seconds))


class CircleIconButton(QToolButton):
    def __init__(self, icon_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.icon_pixmap = QPixmap(_asset(icon_name))
        self.is_enter = False
        self.is_pressed = False
        self.setFixedSize(47, 47)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QToolButton{border:none;margin:0;background:transparent;}")

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.is_enter = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.is_enter = False
        self.update()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.is_pressed = event.button() == Qt.LeftButton
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.is_pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        painter.setPen(Qt.NoPen)
        if self.is_pressed:
            self._paint_pressed(painter)
            return
        if self.is_enter:
            self._paint_hover(painter)
        painter.drawPixmap(1, 1, 45, 45, self.icon_pixmap)

    def _paint_hover(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor(0, 0, 0, 38)))
        painter.setBrush(QBrush(QColor(0, 0, 0, 26)))
        painter.drawEllipse(1, 1, 44, 44)
        painter.setPen(Qt.NoPen)

    def _paint_pressed(self, painter: QPainter) -> None:
        painter.setBrush(QBrush(QColor(0, 0, 0, 45)))
        painter.drawEllipse(2, 2, 42, 42)
        pixmap = self.icon_pixmap.scaled(43, 43, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(2, 2, 42, 42, pixmap)


class PlayButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_playing = False
        self.is_enter = False
        self.is_pressed = False
        self.play_pixmap = QPixmap(_asset("Play.png"))
        self.pause_pixmap = QPixmap(_asset("Pause.png"))
        self.setFixedSize(65, 65)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("QToolButton{border:none;margin:0;background:transparent;}")

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.is_enter = True
        self.update()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.is_enter = False
        self.update()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        self.is_pressed = event.button() == Qt.LeftButton
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.is_pressed = False
        self.update()
        super().mouseReleaseEvent(event)

    def set_playing(self, playing: bool) -> None:
        self.is_playing = playing
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self._paint_circle(painter)
        pixmap = self.pause_pixmap if self.is_playing else self.play_pixmap
        if self.is_pressed:
            pixmap = pixmap.scaled(58, 58, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter.drawPixmap(3, 3, 59, 59, pixmap)
        else:
            painter.drawPixmap(1, 1, 63, 63, pixmap)

    def _paint_circle(self, painter: QPainter) -> None:
        if self.is_pressed:
            painter.setPen(QPen(QColor(255, 255, 255, 120), 2))
            painter.drawEllipse(1, 1, 62, 62)
            return
        if self.is_enter:
            painter.setPen(QPen(QColor(255, 255, 255, 18)))
            painter.drawEllipse(1, 1, 62, 62)
            painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
            painter.drawEllipse(2, 2, 61, 61)
            painter.setPen(QPen(QColor(0, 0, 0, 39)))
            painter.drawEllipse(1, 1, 63, 63)
            return
        painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
        painter.drawEllipse(1, 1, 62, 62)


class VolumeButton(CircleIconButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Volume1.png", parent=parent)
        self.is_muted = False
        self.volume_level = 1
        self.muted_pixmap = QPixmap(_asset("Volumex.png"))
        self.volume_pixmaps = [
            QPixmap(_asset("Volume0.png")),
            QPixmap(_asset("Volume1.png")),
            QPixmap(_asset("Volume2.png")),
            QPixmap(_asset("Volume3.png")),
        ]

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.is_muted = not self.is_muted
            self._sync_icon()
        super().mouseReleaseEvent(event)

    def set_volume(self, volume: int) -> None:
        if volume <= 0:
            self.volume_level = 0
        elif volume < 35:
            self.volume_level = 1
        elif volume < 70:
            self.volume_level = 2
        else:
            self.volume_level = 3
        self.is_muted = volume <= 0
        self._sync_icon()

    def set_muted(self, muted: bool) -> None:
        self.is_muted = muted
        self._sync_icon()

    def _sync_icon(self) -> None:
        self.icon_pixmap = self.muted_pixmap if self.is_muted else self.volume_pixmaps[self.volume_level]
        self.update()


class ModeButton(CircleIconButton):
    modeChanged = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("RepeatAll.png", parent=parent)
        self.mode = PlaybackMode.LIST_LOOP
        self._mode_order = [
            PlaybackMode.LIST_LOOP,
            PlaybackMode.RANDOM,
            PlaybackMode.SINGLE_LOOP,
        ]

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            next_index = (self._mode_order.index(self.mode) + 1) % len(self._mode_order)
            self.set_mode(self._mode_order[next_index])
            self.modeChanged.emit(self.mode)
        super().mouseReleaseEvent(event)

    def set_mode(self, mode: PlaybackMode) -> None:
        self.mode = mode
        if mode == PlaybackMode.RANDOM:
            icon_name = "Shuffle.png"
        elif mode == PlaybackMode.SINGLE_LOOP:
            icon_name = "RepeatOne.png"
        else:
            icon_name = "RepeatAll.png"
        self.icon_pixmap = QPixmap(_asset(icon_name))
        self.update()


class SongTextWidget(QWidget):
    def __init__(self, song: PlayBarSongInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.song = song
        self.setFixedSize(250, 115)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def set_song(self, song: PlayBarSongInfo) -> None:
        self.song = song
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        painter.setPen(Qt.white)

        painter.setFont(_font(19, QFont.Normal))
        title = QFontMetrics(painter.font()).elidedText(self.song.title, Qt.ElideRight, self.width())
        painter.drawText(0, 54, title)

        painter.setFont(_font(17, QFont.DemiBold))
        subtitle = f"{self.song.singer} - {self.song.album}"
        text = QFontMetrics(painter.font()).elidedText(subtitle, Qt.ElideRight, self.width())
        painter.drawText(0, 82, text)


class PlayBarSongCard(QWidget):
    clicked = pyqtSignal()

    def __init__(self, song: PlayBarSongInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cover_label = QLabel(self)
        self.text_widget = SongTextWidget(song, self)
        self.mask = QWidget(self)
        self._init_widget(song)

    def set_song(self, song: PlayBarSongInfo) -> None:
        self.setVisible(bool(song.title or song.singer or song.album))
        self.text_widget.set_song(song)
        self._set_cover(song.cover)

    def set_cover_pixmap(self, pixmap: QPixmap) -> None:
        if pixmap.isNull():
            return
        self.cover_label.setPixmap(pixmap.scaled(115, 115, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

    def set_default_cover(self) -> None:
        self._set_cover(DEFAULT_COVER)

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.mask.show()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.mask.hide()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.cover_label.geometry().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def _init_widget(self, song: PlayBarSongInfo) -> None:
        self.setFixedSize(405, 115)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.cover_label.setGeometry(0, 0, 115, 115)
        self.text_widget.move(130, 0)
        self.mask.setGeometry(0, 0, 115, 115)
        self.mask.setStyleSheet("background: rgba(0, 0, 0, 25);")
        self.mask.hide()
        self.setVisible(bool(song.title or song.singer or song.album))
        self._set_cover(song.cover)

    def _set_cover(self, cover: str) -> None:
        pixmap = QPixmap(cover or DEFAULT_COVER)
        if pixmap.isNull():
            pixmap = QPixmap(DEFAULT_COVER)
        self.cover_label.setPixmap(pixmap.scaled(115, 115, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))


class CentralButtonGroup(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.previous_button = CircleIconButton("Previous.png", parent=self)
        self.play_button = PlayButton(self)
        self.next_button = CircleIconButton("Next.png", parent=self)
        self.mode_button = ModeButton(self)
        self.setFixedSize(251, 78)
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        x = 0
        for button in [
            self.previous_button,
            self.play_button,
            self.next_button,
            self.mode_button,
        ]:
            y = 8 + (65 - button.height()) // 2
            button.move(x, y)
            x += button.width() + 16


class RightWidgetGroup(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.volume_button = VolumeButton(self)
        self.volume_slider = ClickableSlider(Qt.Horizontal, self)
        self.setFixedSize(221, 83)
        self._init_widget()

    def _init_widget(self) -> None:
        self.volume_button.move(7, 16)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(28)
        self.volume_slider.setFixedSize(151, 28)
        self.volume_slider.setStyle(HollowHandleStyle({"sub-page.color": QColor(255, 255, 255)}))
        self.volume_slider.move(62, 25)


class PlayProgressBar(QWidget):
    def __init__(self, duration: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_label = TimeLabel(65, self)
        self.slider = ClickableSlider(Qt.Horizontal, self)
        self.total_label = TimeLabel(duration, self)
        self.setFixedSize(450, 30)
        self._init_widget(duration)

    def set_total_time(self, duration: int) -> None:
        self.total_label.set_time(duration)
        self.slider.setRange(0, duration * 1000)

    def reset(self) -> None:
        self.current_label.set_time(0)
        self.total_label.set_time(0)
        self.slider.setRange(0, 0)
        self.slider.setValue(0)

    def set_current_time(self, position: int) -> None:
        self.slider.blockSignals(True)
        self.slider.setValue(position)
        self.slider.blockSignals(False)
        self.current_label.set_time(position // 1000)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.total_label.move(self.width() - 38, 4)
        self.slider.setGeometry(48, 1, max(40, self.width() - 96), 28)

    def _init_widget(self, duration: int) -> None:
        self.current_label.setGeometry(0, 4, 38, 22)
        self.slider.setRange(0, duration * 1000)
        self.slider.setValue(65 * 1000)
        self.slider.setFixedHeight(28)
        self.slider.setStyle(HollowHandleStyle())
        self.total_label.setGeometry(self.width() - 38, 4, 38, 22)
        self.slider.setGeometry(48, 1, self.width() - 96, 28)
        self.slider.valueChanged.connect(lambda value: self.current_label.set_time(value // 1000))


class PlayBar(QWidget):
    """Bottom playback bar."""

    playPauseRequested = pyqtSignal()
    previousRequested = pyqtSignal()
    nextRequested = pyqtSignal()
    modeChanged = pyqtSignal(object)
    volumeChanged = pyqtSignal(int)
    muteRequested = pyqtSignal()
    positionChanged = pyqtSignal(int)
    songCardClicked = pyqtSignal()

    def __init__(self, song: PlayBarSongInfo | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.old_width = 1280
        self._color = QColor(BAR_COLOR)
        self.color_animation = QPropertyAnimation(self, b"barColor", self)
        self.color_animation.setDuration(260)
        self.song = song or PlayBarSongInfo("", "", "", 0)
        self.song_card = PlayBarSongCard(self.song, self)
        self.central_group = CentralButtonGroup(self)
        self.progress_bar = PlayProgressBar(self.song.duration, self)
        self.right_group = RightWidgetGroup(self)
        self.setFixedHeight(115)
        self._adjust_widgets()
        self._connect_signals()

    def set_song(self, song: PlayBarSongInfo) -> None:
        self.song = song
        self.song_card.set_song(song)
        self.progress_bar.set_total_time(song.duration)

    def clear_song(self) -> None:
        self.set_song(PlayBarSongInfo("", "", "", 0))
        self.song_card.hide()
        self.progress_bar.reset()
        self.set_playing(False)

    def set_playing(self, playing: bool) -> None:
        self.central_group.play_button.set_playing(playing)

    def set_volume(self, volume: int) -> None:
        self.right_group.volume_slider.blockSignals(True)
        self.right_group.volume_slider.setValue(volume)
        self.right_group.volume_slider.blockSignals(False)
        self.right_group.volume_button.set_volume(volume)

    def set_muted(self, muted: bool) -> None:
        self.right_group.volume_button.set_muted(muted)

    def set_position(self, position: int) -> None:
        self.progress_bar.set_current_time(position)

    def set_mode(self, mode: PlaybackMode) -> None:
        self.central_group.mode_button.set_mode(mode)

    def set_cover_pixmap(self, pixmap: QPixmap) -> None:
        self.song_card.set_cover_pixmap(pixmap)

    def set_default_cover(self) -> None:
        self.song_card.set_default_cover()

    def animate_color(self, color: QColor) -> None:
        target_color = DARK_BAR_COLOR if isDarkTheme() else color
        self.color_animation.stop()
        self.color_animation.setStartValue(self.get_bar_color())
        self.color_animation.setEndValue(target_color)
        self.color_animation.start()

    def resizeEvent(self, event) -> None:
        width_delta = self.width() - self.old_width
        new_width = max(320, self.progress_bar.width() + width_delta // 3)
        self.progress_bar.resize(new_width, self.progress_bar.height())
        self._adjust_widgets()
        self.old_width = self.width()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRect(self.rect())

    def set_bar_color(self, color: QColor) -> None:
        self._color = QColor(color)
        self.update()

    def get_bar_color(self) -> QColor:
        return self._color

    def default_color(self) -> QColor:
        if isDarkTheme():
            return QColor(DARK_BAR_COLOR)
        return QColor(BAR_COLOR)

    def _adjust_widgets(self) -> None:
        width = self.width()
        self.central_group.move((width - self.central_group.width()) // 2, 0)
        self.progress_bar.move((width - self.progress_bar.width()) // 2, self.central_group.height())
        self.right_group.move(width - self.right_group.width(), 0)

    def _connect_signals(self) -> None:
        self.central_group.play_button.clicked.connect(self.playPauseRequested)
        self.central_group.previous_button.clicked.connect(self.previousRequested)
        self.central_group.next_button.clicked.connect(self.nextRequested)
        self.central_group.mode_button.modeChanged.connect(self.modeChanged)
        self.right_group.volume_button.clicked.connect(self.muteRequested)
        self.right_group.volume_slider.valueChanged.connect(self.volumeChanged)
        self.progress_bar.slider.clicked.connect(self.positionChanged)
        self.progress_bar.slider.sliderMoved.connect(self.positionChanged)
        self.song_card.clicked.connect(self.songCardClicked)

    barColor = pyqtProperty(QColor, get_bar_color, set_bar_color)
