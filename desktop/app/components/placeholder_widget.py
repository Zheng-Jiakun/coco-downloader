# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtSvg import QSvgWidget

from qfluentwidgets import SimpleCardWidget, setFont


class PlaceholderWidget(SimpleCardWidget):
    """Placeholder widget with illustration and text"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.vBoxLayout = QVBoxLayout(self)

        self.svgWidget = QSvgWidget(self)
        self.titleLabel = QLabel(self.tr("开始搜索音乐"), self)
        self.descLabel = QLabel(
            self.tr("在上方输入歌曲、歌手名称\n选择平台后按回车开始搜索"),
            self
        )

        self._init_ui()

    def _init_ui(self):
        self.svgWidget.load(":/app/images/undraw_location-search.svg")
        self.svgWidget.setFixedSize(350, 250)

        setFont(self.titleLabel, 20, QFont.Weight.Bold)
        setFont(self.descLabel, 14, QFont.Weight.Normal)

        self.titleLabel.setObjectName('titleLabel')
        self.descLabel.setObjectName('descLabel')
        self.titleLabel.setAlignment(Qt.AlignCenter)
        self.descLabel.setAlignment(Qt.AlignCenter)

        self.vBoxLayout.setSpacing(16)
        self.vBoxLayout.setContentsMargins(24, 40, 24, 40)
        self.vBoxLayout.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.addStretch(1)
        self.vBoxLayout.addWidget(self.svgWidget, 0, Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignCenter)
        self.vBoxLayout.addWidget(self.descLabel, 0, Qt.AlignCenter)
        self.vBoxLayout.addStretch(1)

    def set_content_visible(self, visible: bool) -> None:
        """Show or hide illustration and description content."""
        self.svgWidget.setVisible(visible)
        self.titleLabel.setVisible(visible)
        self.descLabel.setVisible(visible)
