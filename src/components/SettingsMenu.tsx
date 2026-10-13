"use client";

import { useEffect, useRef, useState } from "react";
import { Settings, X } from "lucide-react";
import { useDownloadSettings } from "./DownloadSettingsProvider";
import { cn } from "@/lib/utils";

function SettingSwitch({
  id,
  label,
  description,
  checked,
  disabled = false,
  onChange,
}: {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  disabled?: boolean;
  onChange: () => void;
}) {
  return (
    <div className="py-4">
      <div className="flex items-center justify-between gap-4">
        <span id={`${id}-label`} className="text-sm font-medium text-slate-700 dark:text-slate-200">{label}</span>
        <button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-labelledby={`${id}-label`}
          aria-describedby={`${id}-description`}
          disabled={disabled}
          onClick={onChange}
          className="flex h-11 w-14 shrink-0 cursor-pointer items-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <span className={cn("relative inline-flex h-8 w-14 items-center rounded-full transition-colors", checked ? "bg-sky-500" : "bg-slate-300 dark:bg-slate-700")}>
            <span className={cn("h-6 w-6 rounded-full bg-white shadow-sm transition-transform", checked ? "translate-x-7" : "translate-x-1")} />
          </span>
        </button>
      </div>
      <p id={`${id}-description`} className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{description}</p>
    </div>
  );
}

export function SettingsMenu({
  autoSystem,
  onToggleAutoSystem,
}: {
  autoSystem: boolean;
  onToggleAutoSystem: () => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const {
    downloadEnabled,
    nasSaveSupported,
    saveToNasEnabled,
    convertAacToMp3,
    toggleNasSave,
    toggleAacConversion,
  } = useDownloadSettings();

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();

    const handlePointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const handleFocusIn = (event: FocusEvent) => {
      if (event.target instanceof Node && !containerRef.current?.contains(event.target)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("focusin", handleFocusIn);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("focusin", handleFocusIn);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        title="设置"
        aria-label="设置"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls="settings-menu"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex h-11 w-11 cursor-pointer items-center justify-center rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-sky-500",
          open ? "bg-sky-50 text-sky-600 dark:bg-slate-800 dark:text-sky-300" : "text-slate-500 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-sky-300"
        )}
      >
        <Settings className="h-5 w-5" />
      </button>
      {open && (
        <div
          id="settings-menu"
          role="dialog"
          aria-labelledby="settings-menu-title"
          className="absolute right-0 top-[calc(100%+8px)] z-50 max-h-[calc(100dvh-8rem)] w-80 max-w-[calc(100vw-2rem)] overflow-y-auto rounded-2xl border border-slate-200 bg-white p-4 shadow-xl dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="flex items-center justify-between">
            <h2 id="settings-menu-title" className="text-base font-semibold text-slate-800 dark:text-slate-100">设置</h2>
            <button
              ref={closeRef}
              type="button"
              aria-label="关闭设置"
              onClick={() => { setOpen(false); triggerRef.current?.focus(); }}
              className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-sky-500 dark:text-slate-400 dark:hover:bg-slate-800"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className="divide-y divide-slate-100 dark:divide-slate-800">
            <SettingSwitch
              id="nas-save"
              label="保存到 NAS"
              checked={downloadEnabled && nasSaveSupported && saveToNasEnabled}
              disabled={!downloadEnabled || !nasSaveSupported}
              onChange={toggleNasSave}
              description={!downloadEnabled
                ? "下载功能已关闭。"
                : !nasSaveSupported
                  ? "未配置 NAS 挂载目录，当前只能使用浏览器下载。"
                  : saveToNasEnabled
                    ? "下载结果写入 NAS 挂载目录，按歌手/专辑/歌曲命名。"
                    : "当前使用浏览器下载，开启后改为保存到 NAS。"}
            />
            <SettingSwitch
              id="aac-conversion"
              label="AAC 自动转 MP3"
              checked={convertAacToMp3}
              disabled={!downloadEnabled}
              onChange={toggleAacConversion}
              description={downloadEnabled
                ? "仅将 AAC（含 M4A 中的 AAC）转为 MP3，其他编码不变；转换需要额外时间，仅影响新建任务。"
                : "下载功能已关闭。"}
            />
            <SettingSwitch
              id="auto-theme"
              label="自动深色模式"
              checked={autoSystem}
              onChange={onToggleAutoSystem}
              description="跟随系统自动切换深色或浅色主题。"
            />
          </div>
        </div>
      )}
    </div>
  );
}
