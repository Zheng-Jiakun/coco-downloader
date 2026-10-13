# coding: utf-8
from PyQt5.QtCore import QObject, pyqtSignal


class SignalBus(QObject):
    """ Signal bus """

    checkUpdateSig = pyqtSignal()
    micaEnableChanged = pyqtSignal(bool)
    switchToPlayingInterfaceRequested = pyqtSignal()
    playPlaylistRequested = pyqtSignal(list, int)
    playbackToggleRequested = pyqtSignal()
    playbackPreviousRequested = pyqtSignal()
    playbackNextRequested = pyqtSignal()
    playbackSeekRequested = pyqtSignal(int)
    playbackVolumeChanged = pyqtSignal(int)
    playbackMuteRequested = pyqtSignal()
    playbackModeChanged = pyqtSignal(object)
    playbackError = pyqtSignal(str)
    playbackTrackChanged = pyqtSignal(object, int)
    playbackStateChanged = pyqtSignal(bool)
    playbackPositionChanged = pyqtSignal(int)
    playbackDurationChanged = pyqtSignal(int)
    playbackCoverChanged = pyqtSignal(object, object)
    downloadStarted = pyqtSignal(str, object)
    downloadRequested = pyqtSignal(object, object)
    downloadTaskUpdated = pyqtSignal(object)
    downloadProgressChanged = pyqtSignal(object, object)
    downloadRetryRequested = pyqtSignal(object)
    downloadCancelRequested = pyqtSignal(object)
    downloadFinished = pyqtSignal(str, object)
    downloadFailed = pyqtSignal(str, object)


signalBus = SignalBus()
