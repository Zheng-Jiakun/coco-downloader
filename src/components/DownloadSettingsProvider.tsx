"use client";

import { createContext, useContext, useEffect, useState } from "react";

type DownloadSettings = {
  downloadEnabled: boolean;
  nasSaveSupported: boolean;
  saveToNasEnabled: boolean;
  convertAacToMp3: boolean;
  toggleNasSave: () => void;
  toggleAacConversion: () => void;
};

const DownloadSettingsContext = createContext<DownloadSettings | null>(null);

export function DownloadSettingsProvider({
  children,
  downloadEnabled,
  nasSaveSupported,
}: {
  children: React.ReactNode;
  downloadEnabled: boolean;
  nasSaveSupported: boolean;
}) {
  const [saveToNasEnabled, setSaveToNasEnabled] = useState(nasSaveSupported);
  const [convertAacToMp3, setConvertAacToMp3] = useState(true);

  useEffect(() => {
    try {
      // Restore the browser preference after hydration to keep server markup stable.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setConvertAacToMp3(localStorage.getItem("coco:convertAacToMp3") !== "0");
    } catch {
      // Keep the default when browser storage is unavailable.
    }
  }, []);

  const toggleNasSave = () => {
    if (downloadEnabled && nasSaveSupported) {
      setSaveToNasEnabled((enabled) => !enabled);
    }
  };

  const toggleAacConversion = () => {
    if (!downloadEnabled) return;
    const next = !convertAacToMp3;
    setConvertAacToMp3(next);
    try {
      localStorage.setItem("coco:convertAacToMp3", next ? "1" : "0");
    } catch {
      // The toggle still works for this session without browser storage.
    }
  };

  return (
    <DownloadSettingsContext.Provider value={{
      downloadEnabled,
      nasSaveSupported,
      saveToNasEnabled,
      convertAacToMp3,
      toggleNasSave,
      toggleAacConversion,
    }}>
      {children}
    </DownloadSettingsContext.Provider>
  );
}

export function useDownloadSettings() {
  const settings = useContext(DownloadSettingsContext);
  if (!settings) {
    throw new Error("useDownloadSettings must be used within DownloadSettingsProvider");
  }
  return settings;
}
