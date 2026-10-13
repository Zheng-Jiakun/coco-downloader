import unittest
from unittest.mock import Mock, patch

from app.services.errors import ProviderNetworkError
from app.services.providers.bodian import BodianProvider
from app.services.providers.jianbin_session import initialize_session
from app.services.providers.migu import MiguProvider
from app.services.providers.qq import QQProvider
from app.services.providers.qqmp3 import QQMp3Provider
from app.models.music import PlayInfo


class ProviderRepairTests(unittest.TestCase):
    def test_qqmp3_expired_audio_uses_backup(self):
        provider = QQMp3Provider()
        provider._http = Mock()
        provider._http.get_json.return_value = {"code": 200, "data": {"url": "https://example.com/a.mp3"}}
        with patch("app.services.providers.qqmp3.validate_audio_url", side_effect=[ValueError("HTTP 410"), "https://example.com/valid.mp3"]):
            self.assertEqual(provider.get_play_info("50").url, "https://example.com/valid.mp3")
        self.assertEqual(provider._http.get_json.call_count, 2)
        self.assertIn("bb.qqmp3.vip", provider._http.get_json.call_args.args[0])

    def test_qq_preview_uses_mp3_without_lowering_download_quality(self):
        provider = QQProvider()
        with patch.object(provider, "_get_by_vkeys", return_value=PlayInfo("https://example.com/a.mp3", "mp3")) as resolve:
            provider.get_play_info("mid", {"usage": "playback"})
            resolve.assert_called_once_with("mid", (8, 6))
            resolve.reset_mock()
            provider.get_play_info("mid", {})
            resolve.assert_called_once_with("mid")

    def test_jianbin_initializes_only_the_published_visitor_cookie(self):
        import requests
        session = requests.Session()
        response = Mock()
        response.text = '<script>document.cookie="mk_visit=123-abc;path=/;max-age=43200";location.replace("/");</script>'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        session.get = Mock(return_value=response)
        initialize_session(session, {}, 10)
        self.assertEqual(session.cookies.get("mk_visit"), "123-abc")
        self.assertEqual(session.get.call_count, 2)

    def test_bodian_network_error_reaches_backup(self):
        provider = BodianProvider()
        with patch.object(provider, "_get_by_tianbao", side_effect=ProviderNetworkError("ssl", "SSL failed")), patch.object(provider, "_get_by_cenguigui", return_value={"url": "https://example.com/a.mp3"}) as backup:
            self.assertEqual(provider.get_play_info("1").url, "https://example.com/a.mp3")
            backup.assert_called_once_with("1")

    def test_migu_retains_metadata_and_does_not_research_by_id(self):
        provider = MiguProvider()
        item = provider._map_item({"contentId": "1", "copyrightId": "2", "rateFormats": [{"formatType": "HQ", "resourceType": "2"}]})
        provider._http = Mock()
        provider._http.get_json.return_value = {"data": {"url": "https://example.com/MP3_128_16_Stero/a.mp3"}}
        with patch.object(provider, "_find_song") as research, patch("app.services.providers.migu.validate_audio_url", side_effect=lambda http, url, **kwargs: url):
            info = provider.get_play_info(item.id, item.extra)
            research.assert_not_called()
            self.assertIn("MP3_128_16_Stero", info.url)

    def test_migu_rejects_json_and_tries_next_quality(self):
        provider = MiguProvider()
        provider._http = Mock()
        provider._http.get_json.return_value = {"code": "201007"}
        rate = {"formatType": "SQ", "resourceType": "E"}
        song = {"rateFormats": [rate, rate, {"formatType": "HQ", "resourceType": "2"}]}
        with patch("app.services.providers.migu.validate_audio_url", side_effect=[ValueError("Non-audio content type: application/json"), "https://example.com/a.mp3"]) as validate:
            info = provider.get_play_info("1_2", {"song": song})
            self.assertEqual(validate.call_count, 2)
            self.assertEqual(info.bitrate, "HQ")

    def test_migu_does_not_use_unrelated_search_result(self):
        provider = MiguProvider()
        provider._http = Mock()
        provider._http.get_json.return_value = {"songResultData": {"result": [{"contentId": "other"}]}}
        self.assertIsNone(provider._find_song("requested"))


if __name__ == "__main__":
    unittest.main()
