# coding: utf-8
from enum import Enum

from qfluentwidgets import StyleSheetBase, Theme, isDarkTheme, qconfig


class StyleSheet(StyleSheetBase, Enum):
    """ Style sheet  """

    # TODO: Add your qss here

    HOME_INTERFACE = "home_interface"
    SETTING_INTERFACE = "setting_interface"
    SONG_LIST_WIDGET = "song_list_widget"
    DOWNLOAD_INTERFACE = "download_interface"

    def path(self, theme=Theme.AUTO):
        theme = qconfig.theme if theme == Theme.AUTO else theme
        return f":/app/qss/{theme.value.lower()}/{self.value}.qss"
