"use client";

import Image from "next/image";
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Shuffle, Repeat, Repeat1, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { MusicItem } from "@/types/music";
import { ConfigProvider, Slider } from "antd";

interface PlayerBarProps {
  currentMusic: MusicItem | null;
  isPlaying: boolean;
  onPlayPause: () => void;
  onNext?: () => void;
  onPrev?: () => void;
  playMode: "order" | "shuffle" | "single";
  onTogglePlayMode: () => void;
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
  volume: number;
  onVolumeChange: (volume: number) => void;
  isResolving?: boolean;
  onOpenPlayer?: () => void;
}

export function PlayerBar({
  currentMusic,
  isPlaying,
  onPlayPause,
  onNext,
  onPrev,
  playMode,
  onTogglePlayMode,
  currentTime,
  duration,
  onSeek,
  volume,
  onVolumeChange,
  isResolving = false,
  onOpenPlayer,
}: PlayerBarProps) {
  const formatTime = (time?: number) => {
    const t = typeof time === "number" ? time : 0;
    if (isNaN(t)) return "00:00";
    const minutes = Math.floor(t / 60);
    const seconds = Math.floor(t % 60);
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
  };

  if (!currentMusic) return null;

  const modeLabel = playMode === "shuffle" ? "随机播放" : playMode === "single" ? "单曲循环" : "顺序播放";
  const ModeIcon = playMode === "shuffle" ? Shuffle : playMode === "single" ? Repeat1 : Repeat;

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#0ea5e9",
        },
      }}
    >
      <motion.div
        initial={{ y: 100, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 100, opacity: 0 }}
        className="fixed bottom-0 left-0 right-0 z-50 h-24 bg-white/90 shadow-[0_-4px_20px_rgba(0,0,0,0.18)] backdrop-blur-2xl dark:bg-[#242526]/92"
      >
        <div className="absolute left-0 top-0 h-[2px] w-full overflow-hidden bg-[#e5e2e1] dark:bg-white/10">
          <div
            className="relative h-full bg-[#005faa] dark:bg-[#a3c9ff]"
            style={{ width: `${duration > 0 ? Math.min(100, (currentTime / duration) * 100) : 0}%` }}
          >
            <div className="absolute right-0 top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-[#005faa] shadow-[0_0_8px_rgba(0,120,212,0.8)] dark:bg-[#a3c9ff]" />
          </div>
        </div>

        <div
          onClick={onOpenPlayer}
          className="mx-auto flex h-full w-full max-w-[1440px] cursor-pointer items-center justify-between gap-4 px-4 pt-2 md:px-6"
        >
          <button
            type="button"
            onClick={onOpenPlayer}
            className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 rounded-lg text-left transition-colors hover:bg-[#005faa]/5 md:w-1/3 dark:hover:bg-white/5"
          >
            <div className="relative h-12 w-12 flex-shrink-0 overflow-hidden rounded-md border border-[#c0c7d4]/20 bg-[#f0eded] shadow-sm dark:border-white/10 dark:bg-[#303030]">
              {currentMusic.cover ? (
                <Image
                  src={currentMusic.cover}
                  alt={currentMusic.title}
                  fill
                  sizes="48px"
                  className="object-cover"
                  unoptimized
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-[#d3e3ff] font-bold text-[#005faa] dark:bg-[#003f6d] dark:text-[#a3c9ff]">
                  {currentMusic.title[0]}
                </div>
              )}
            </div>
            <div className="hidden min-w-0 flex-col overflow-hidden sm:flex">
              <h3 className="truncate text-sm font-medium leading-5 text-[#1b1b1c] dark:text-[#f3f0ef]">{currentMusic.title}</h3>
              <p className="truncate text-xs font-medium leading-4 text-[#404752] dark:text-[#c6c6c7]">
                {isResolving ? "正在解析音源..." : currentMusic.artist}
              </p>
            </div>
          </button>

          <div className="flex items-center justify-center gap-3 sm:gap-5 md:hidden" onClick={(e) => e.stopPropagation()}>
            <button 
              onClick={onPlayPause}
              disabled={isResolving}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[#005faa] text-white shadow-md transition-transform active:scale-95 disabled:cursor-wait"
            >
              {isResolving ? <Loader2 className="w-4 h-4 animate-spin" /> : isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current ml-0.5" />}
            </button>
            <button 
              onClick={onNext}
              disabled={!onNext}
              className="text-[#404752] active:text-[#005faa] disabled:opacity-30 dark:text-[#c6c6c7] dark:active:text-[#a3c9ff]"
            >
               <SkipForward className="w-6 h-6" />
            </button>
            <button
              onClick={onTogglePlayMode}
              className="text-[#404752] active:text-[#005faa] dark:text-[#c6c6c7] dark:active:text-[#a3c9ff]"
              title={modeLabel}
            >
              <ModeIcon className="w-5 h-5" />
            </button>
          </div>

          <div className="hidden flex-1 cursor-default flex-col items-center justify-center md:flex md:w-1/3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-6">
              <button 
                onClick={onPrev}
                disabled={!onPrev}
                className="cursor-pointer text-[#404752] transition-colors hover:text-[#005faa] disabled:opacity-30 dark:text-[#c6c6c7] dark:hover:text-[#a3c9ff]"
              >
                <SkipBack className="w-5 h-5" />
              </button>

              <button 
                onClick={onPlayPause}
                disabled={isResolving}
                className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full bg-[#005faa] text-white shadow-lg shadow-[#005faa]/25 transition-all hover:bg-[#0078d4] active:scale-95 disabled:cursor-wait"
              >
                {isResolving ? <Loader2 className="w-5 h-5 animate-spin" /> : isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current ml-0.5" />}
              </button>
              
              <button 
                onClick={onNext}
                disabled={!onNext}
                className="cursor-pointer text-[#404752] transition-colors hover:text-[#005faa] disabled:opacity-30 dark:text-[#c6c6c7] dark:hover:text-[#a3c9ff]"
              >
                <SkipForward className="w-5 h-5" />
              </button>

              <button
                onClick={onTogglePlayMode}
                className="cursor-pointer text-[#404752] transition-colors hover:text-[#005faa] dark:text-[#c6c6c7] dark:hover:text-[#a3c9ff]"
                title={modeLabel}
              >
                <ModeIcon className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex w-full items-center gap-3 text-xs font-medium text-[#404752] dark:text-[#c6c6c7]">
              <span className="w-10 text-right tabular-nums">{formatTime(currentTime)}</span>
              <div className="flex-1 px-2">
                <Slider
                  min={0}
                  max={duration || 100}
                  value={currentTime}
                  onChange={onSeek}
                  tooltip={{ formatter: formatTime }}
                  styles={{
                    track: { background: "#005faa" },
                    rail: { background: "#e5e2e1" },
                    handle: { borderColor: "#005faa" }
                  }}
                />
              </div>
              <span className="w-10 tabular-nums">{formatTime(duration)}</span>
            </div>
          </div>

          <div className="hidden min-w-[150px] cursor-default items-center justify-end gap-4 md:flex md:w-1/3" onClick={(e) => e.stopPropagation()}>
            <div className="group flex w-32 items-center gap-2">
              <button 
                onClick={() => onVolumeChange(volume === 0 ? 1 : 0)}
                className="cursor-pointer text-[#404752] transition-colors hover:text-[#005faa] dark:text-[#c6c6c7] dark:hover:text-[#a3c9ff]"
              >
                {volume === 0 ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
              </button>
              <div className="flex-1 w-24">
                <Slider
                  min={0}
                  max={1}
                  step={0.01}
                  value={volume}
                  onChange={onVolumeChange}
                  tooltip={{ formatter: (val) => `${Math.round((val || 0) * 100)}%` }}
                  styles={{
                    track: { background: "#005faa" },
                    rail: { background: "#e5e2e1" },
                    handle: { borderColor: "#005faa" }
                  }}
                />
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </ConfigProvider>
  );
}
