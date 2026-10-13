# coding: utf-8
from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsDropShadowEffect, QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import Action, BodyLabel, CaptionLabel, CommandBarView, FluentIcon, IconWidget, ScrollArea
from qfluentwidgets import SegmentedWidget, isDarkTheme, setFont

from app.common.signal_bus import signalBus
from app.common.icon import Logo
from app.common.style_sheet import StyleSheet
from app.components.download_task_card import DownloadTaskCard
from app.services.download_service import DownloadTaskInfo, DownloadTaskStatus


class EmptyStatusWidget(QWidget):
    """Small empty state card matching Fluent-M3U8 task page."""

    def __init__(self, text: str, parent=None) -> None:
        super().__init__(parent)
        self.iconWidget = IconWidget(Logo.SMILEFACE, self)
        self.label = CaptionLabel(text, self)
        self.vBoxLayout = QVBoxLayout(self)
        self._init_widget()

    def setText(self, text: str) -> None:
        self.label.setText(text)

    def _init_widget(self) -> None:
        self.setObjectName("emptyStatusWidget")
        self.iconWidget.setFixedSize(80, 80)
        self.label.setAlignment(Qt.AlignCenter)
        self.vBoxLayout.setSpacing(10)
        self.vBoxLayout.setContentsMargins(16, 20, 16, 20)
        self.vBoxLayout.addWidget(self.iconWidget, 0, Qt.AlignHCenter)
        self.vBoxLayout.addWidget(self.label, 0, Qt.AlignHCenter)


class DownloadTaskView(QWidget):
    """Task card list with selection command bar."""

    cardCountChanged = pyqtSignal(int)
    retryTaskRequested = pyqtSignal(object)

    def __init__(self, status: DownloadTaskStatus, parent=None) -> None:
        super().__init__(parent)
        self.status = status
        self.cards: list[DownloadTaskCard] = []
        self.cardMap: dict[str, DownloadTaskCard] = {}
        self.selectionCount = 0
        self.isSelectionMode = False
        self.commandView = DownloadCommandBarView(self)
        self.vBoxLayout = QVBoxLayout(self)
        self._init_widget()
        self._init_command_bar()
        self._connect_signals()

    def addTask(self, task: DownloadTaskInfo) -> None:
        card = DownloadTaskCard(task, self)
        card.deleted.connect(self._on_task_deleted)
        card.checkedChanged.connect(self._on_card_checked_changed)
        card.retryRequested.connect(self.retryTaskRequested)
        if self.isSelectionMode:
            card.setSelectionMode(True)

        self.vBoxLayout.insertWidget(0, card, 0, Qt.AlignTop)
        self.cards.insert(0, card)
        self.cardMap[task.id] = card
        self.cardCountChanged.emit(self.count())

    def removeTask(self, task: DownloadTaskInfo) -> None:
        card = self.cardMap.pop(task.id, None)
        if card is None:
            return
        self.cards.remove(card)
        self.vBoxLayout.removeWidget(card)
        if card.isChecked():
            self.selectionCount = max(0, self.selectionCount - 1)
        card.hide()
        card.deleteLater()
        self.cardCountChanged.emit(self.count())
        if self.selectionCount <= 0:
            self.setSelectionMode(False)

    def moveTaskTo(self, task: DownloadTaskInfo, target: "DownloadTaskView") -> None:
        self.removeTask(task)
        target.addTask(task)

    def findCard(self, task: DownloadTaskInfo) -> DownloadTaskCard | None:
        return self.cardMap.get(task.id)

    def updateTask(self, task: DownloadTaskInfo) -> None:
        card = self.findCard(task)
        if card is not None:
            card.update_task(task)

    def count(self) -> int:
        return len(self.cards)

    def setSelectionMode(self, enter: bool) -> None:
        if self.isSelectionMode == enter:
            return

        self.isSelectionMode = enter
        for card in self.cards:
            card.setSelectionMode(enter)
        self.commandView.setVisible(enter)
        if enter:
            self.commandView.raise_()
            self.update_command_view_position()
        else:
            self.selectionCount = 0

    def selectAll(self) -> None:
        for card in self.cards:
            card.setChecked(True)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_command_view_position()

    def update_command_view_position(self) -> None:
        x = (self.width() - self.commandView.width()) // 2
        y = self.height() - self.commandView.sizeHint().height() - 20
        self.commandView.move(max(0, x), max(0, y))

    def _init_widget(self) -> None:
        self.vBoxLayout.setSpacing(5)
        self.vBoxLayout.setContentsMargins(30, 0, 30, 0)
        self.vBoxLayout.setAlignment(Qt.AlignTop)
        self.commandView.hide()

    def _init_command_bar(self) -> None:
        if self.status == DownloadTaskStatus.DOWNLOADING:
            self.commandView.setRetryVisible(False)

    def _connect_signals(self) -> None:
        self.commandView.deleteAction.triggered.connect(self._remove_selected_tasks)
        self.commandView.retryAction.triggered.connect(self._retry_selected_tasks)
        self.commandView.selectAllAction.triggered.connect(self.selectAll)
        self.commandView.cancelAction.triggered.connect(lambda: self.setSelectionMode(False))

    def _on_card_checked_changed(self, checked: bool) -> None:
        self.selectionCount += 1 if checked else -1
        if checked:
            self.setSelectionMode(True)
        elif self.selectionCount <= 0:
            self.setSelectionMode(False)

    def _on_task_deleted(self, task: DownloadTaskInfo) -> None:
        if task.status in {DownloadTaskStatus.PENDING, DownloadTaskStatus.DOWNLOADING}:
            signalBus.downloadCancelRequested.emit(task)
        self.removeTask(task)

    def _remove_selected_tasks(self) -> None:
        for card in self.cards.copy():
            if card.isChecked():
                if card.task.status in {DownloadTaskStatus.PENDING, DownloadTaskStatus.DOWNLOADING}:
                    signalBus.downloadCancelRequested.emit(card.task)
                self.removeTask(card.task)

    def _retry_selected_tasks(self) -> None:
        for card in self.cards:
            if card.isChecked():
                self.retryTaskRequested.emit(card.task)


class DownloadCommandBarView(CommandBarView):
    """Bottom command bar for selected download tasks."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.retryAction = Action(FluentIcon.UPDATE, self.tr("重新下载"), self)
        self.deleteAction = Action(FluentIcon.DELETE, self.tr("删除"), self)
        self.selectAllAction = Action(FluentIcon.CHECKBOX, self.tr("全选"), self)
        self.cancelAction = Action(FluentIcon.CLEAR_SELECTION, self.tr("取消"), self)

        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(18, 18))
        self.addActions([self.retryAction, self.deleteAction])
        self.addSeparator()
        self.addActions([self.selectAllAction, self.cancelAction])
        self.resizeToSuitableWidth()
        self._set_shadow_effect()

    def setRetryVisible(self, visible: bool) -> None:
        self.retryAction.setVisible(visible)
        command_bar = getattr(self, "bar", None)
        command_buttons = getattr(command_bar, "commandButtons", [])
        if command_buttons:
            command_buttons[0].setVisible(visible)
        self.resizeToSuitableWidth()

    def _set_shadow_effect(self) -> None:
        color = QColor(0, 0, 0, 80 if isDarkTheme() else 30)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(35)
        effect.setOffset(0, 8)
        effect.setColor(color)
        self.setGraphicsEffect(effect)


class DownloadInterface(ScrollArea):
    """Download task list interface."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.view = QWidget(self)
        self.titleLabel = BodyLabel(self.tr("下载列表"), self.view)
        self.pivot = SegmentedWidget(self.view)
        self.stackedWidget = QStackedWidget(self.view)
        self.downloadingTaskView = DownloadTaskView(DownloadTaskStatus.DOWNLOADING, self.view)
        self.finishedTaskView = DownloadTaskView(DownloadTaskStatus.FINISHED, self.view)
        self.failedTaskView = DownloadTaskView(DownloadTaskStatus.FAILED, self.view)
        self.emptyStatusWidget = EmptyStatusWidget(self.tr("当前没有下载任务"), self.view)
        self.vBoxLayout = QVBoxLayout(self.view)

        self._init_widget()
        self._connect_signals()

    def _init_widget(self) -> None:
        self.setObjectName("downloadInterface")
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setObjectName("downloadView")
        setFont(self.titleLabel, 23)
        StyleSheet.DOWNLOAD_INTERFACE.apply(self)

        self.pivot.addItem("downloading", self.tr("下载中"), lambda: self._set_current_view("downloading"))
        self.pivot.addItem("finished", self.tr("已完成"), lambda: self._set_current_view("finished"))
        self.pivot.addItem("failed", self.tr("失败"), lambda: self._set_current_view("failed"))
        self.pivot.setCurrentItem("downloading")

        self.stackedWidget.addWidget(self.downloadingTaskView)
        self.stackedWidget.addWidget(self.finishedTaskView)
        self.stackedWidget.addWidget(self.failedTaskView)

        self.vBoxLayout.setSpacing(20)
        self.vBoxLayout.setContentsMargins(30, 33, 30, 10)
        self.vBoxLayout.addWidget(self.titleLabel)
        self.vBoxLayout.addWidget(self.pivot, 0, Qt.AlignLeft)
        self.vBoxLayout.addWidget(self.stackedWidget, 1)
        self.emptyStatusWidget.resize(260, 145)
        self._update_empty_status()

    def _connect_signals(self) -> None:
        self.stackedWidget.currentChanged.connect(lambda *_: self._on_current_view_changed())
        self.downloadingTaskView.cardCountChanged.connect(lambda *_: self._update_empty_status())
        self.finishedTaskView.cardCountChanged.connect(lambda *_: self._update_empty_status())
        self.failedTaskView.cardCountChanged.connect(lambda *_: self._update_empty_status())
        self.failedTaskView.retryTaskRequested.connect(signalBus.downloadRetryRequested)
        self.finishedTaskView.retryTaskRequested.connect(signalBus.downloadRetryRequested)
        signalBus.downloadStarted.connect(self._on_download_started)
        signalBus.downloadTaskUpdated.connect(self._on_download_task_updated)
        signalBus.downloadProgressChanged.connect(self._on_download_progress_changed)
        signalBus.downloadFinished.connect(self._on_download_finished)
        signalBus.downloadFailed.connect(self._on_download_failed)

    def _set_current_view(self, key: str) -> None:
        mapping = {
            "downloading": self.downloadingTaskView,
            "finished": self.finishedTaskView,
            "failed": self.failedTaskView,
        }
        self.stackedWidget.setCurrentWidget(mapping[key])
        self.pivot.setCurrentItem(key)

    def _on_current_view_changed(self) -> None:
        for task_view in (self.downloadingTaskView, self.finishedTaskView, self.failedTaskView):
            task_view.setSelectionMode(False)
        self._update_empty_status()

    def _on_download_started(self, title: str, task_info: DownloadTaskInfo | None) -> None:
        if task_info is not None:
            self.downloadingTaskView.addTask(task_info)
            self._set_current_view("downloading")

    def _on_download_task_updated(self, task_info: DownloadTaskInfo | None) -> None:
        if task_info is None:
            return
        card = self.downloadingTaskView.findCard(task_info)
        if card is not None:
            card.update_task(task_info)

    def _on_download_progress_changed(self, task_info: DownloadTaskInfo | None, _progress: object) -> None:
        if task_info is None:
            return
        card = self.downloadingTaskView.findCard(task_info)
        if card is not None:
            card.update_task(task_info)

    def _on_download_finished(self, file_path: str, task_info: DownloadTaskInfo | None) -> None:
        if task_info is None:
            return
        self.downloadingTaskView.updateTask(task_info)
        self.downloadingTaskView.moveTaskTo(task_info, self.finishedTaskView)
        self._update_empty_status()

    def _on_download_failed(self, message: str, task_info: DownloadTaskInfo | None) -> None:
        if task_info is None:
            return
        self.downloadingTaskView.updateTask(task_info)
        self.downloadingTaskView.moveTaskTo(task_info, self.failedTaskView)
        self._update_empty_status()

    def _update_empty_status(self) -> None:
        view = self.stackedWidget.currentWidget()
        count = view.count() if isinstance(view, DownloadTaskView) else 0
        self.emptyStatusWidget.setVisible(count == 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        width = self.emptyStatusWidget.width()
        height = self.emptyStatusWidget.height()
        x = (self.viewport().width() - width) // 2
        y = max(180, (self.viewport().height() - height) // 2)
        self.emptyStatusWidget.move(x, y)
        self._move_current_command_view()

    def _move_current_command_view(self) -> None:
        current_view = self.stackedWidget.currentWidget()
        if isinstance(current_view, DownloadTaskView):
            current_view.update_command_view_position()
