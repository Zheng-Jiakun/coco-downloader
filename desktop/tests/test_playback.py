import socket
import unittest
from unittest.mock import Mock, patch

import requests
from urllib3.exceptions import MaxRetryError, NameResolutionError

from test_desktop import APP, pump_until
from PyQt5.QtCore import QCoreApplication, QEvent
from PyQt5.QtMultimedia import QMediaPlayer
from app.common.signal_bus import signalBus
from app.models.music import MusicItem
from app.services.playback_service import PlaybackService
from app.services.providers.http_client import ProviderHttpClient
from app.services.providers.netease_official import NeteaseOfficialProvider
from app.services.errors import ProviderNetworkError
from app.services.thread_lifecycle import shutdown_threads
from app.view.main_window import MainWindow


class PlaybackTests(unittest.TestCase):
    def test_unexpected_python_exception_shows_toast(self):
        from app.common.error_handler import ErrorReporter
        from PyQt5.QtWidgets import QWidget
        reporter = ErrorReporter(APP)
        reporter.window = QWidget()
        with self.assertLogs("app", level="ERROR"), patch("app.common.error_handler.InfoBar.error") as toast:
            reporter.handle_exception(ValueError, ValueError("channel unavailable"), None)
            APP.processEvents()
            self.assertIn("channel unavailable", toast.call_args.kwargs["content"])
        reporter.window.deleteLater()
        reporter.deleteLater()

    def tearDown(self):
        shutdown_threads()
        APP.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)

    def test_dns_error_identifies_the_service_domain(self):
        client = ProviderHttpClient()
        dns = NameResolutionError("api.qijieya.cn", None, socket.gaierror(11001, "getaddrinfo failed"))
        client._session = Mock()
        client._session.request.side_effect = requests.ConnectionError(MaxRetryError(None, "/meting/", dns))
        with self.assertRaisesRegex(ProviderNetworkError, r"api.qijieya.cn.*DNS"):
            client.get_response("https://api.qijieya.cn/meting/")

    def test_both_resolvers_fail_reports_both_reasons(self):
        provider = NeteaseOfficialProvider()
        with patch.object(provider, "_get_by_meting", side_effect=ValueError("DNS 解析失败")), patch.object(provider, "_get_by_cenguigui", side_effect=ValueError("备用服务超时")), self.assertLogs(level="WARNING"):
            with self.assertRaisesRegex(ValueError, "DNS 解析失败.*备用服务超时"):
                provider.get_play_info("30612793")

    def test_remote_resource_error_emits_once(self):
        service = PlaybackService(Mock())
        service.current_media_path = "https://example.com/song.mp3"
        messages = []
        signalBus.playbackError.connect(messages.append)
        try:
            service._on_player_error(QMediaPlayer.ResourceError)
            service._on_media_status_changed(QMediaPlayer.InvalidMedia)
            self.assertEqual(len(messages), 1)
            self.assertIn("无法加载音频", messages[0])
        finally:
            signalBus.playbackError.disconnect(messages.append)
            service.deleteLater()

    def test_load_timeout_reports_and_ignores_late_result(self):
        service = PlaybackService(Mock())
        worker = Mock()
        service.resolve_thread = worker
        messages = []
        signalBus.playbackError.connect(messages.append)
        try:
            service.load_timer.start(1000)
            service._on_load_timeout()
            worker.requestInterruption.assert_called_once()
            self.assertFalse(service.load_timer.isActive())
            self.assertIn("加载超时", messages[0])
            service.current_index = 0
            with patch.object(service.player, "setMedia") as set_media:
                service._on_media_prepared(0, Mock(url="https://example.com/late.mp3"))
                set_media.assert_not_called()
        finally:
            service.resolve_thread = None
            signalBus.playbackError.disconnect(messages.append)
            service.deleteLater()

    def test_resolver_failure_reaches_real_window_infobar(self):
        window = MainWindow()
        provider = Mock()
        provider.get_play_info.side_effect = ValueError("云音乐 DNS 解析失败")
        try:
            with patch("app.services.playback_service.get_provider", return_value=provider), patch("app.view.main_window.InfoBar.error") as toast:
                window.playbackService.set_playlist([MusicItem("30612793", "test", "artist", "netease")], 0)
                pump_until(lambda: window.playbackService.resolve_thread is None)
                toast.assert_called_once()
                self.assertEqual(toast.call_args.kwargs["content"], "云音乐 DNS 解析失败")
                self.assertIs(toast.call_args.kwargs["parent"], window)
                self.assertFalse(window.playbackService.load_timer.isActive())
        finally:
            window.hide()
            window.deleteLater()


if __name__ == "__main__":
    unittest.main()
