"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import Image from "next/image";
import { AnimatePresence, motion } from "framer-motion";
import { Pause, Play, SkipBack, SkipForward, X } from "lucide-react";
import { ConfigProvider, Slider } from "antd";
import { cn } from "@/lib/utils";
import { MusicItem } from "@/types/music";

type LyricLine = {
  time: number;
  text: string;
};

interface FullscreenPlayerDrawerProps {
  isOpen: boolean;
  music: MusicItem | null;
  isPlaying: boolean;
  lyrics: LyricLine[];
  lyricLoading?: boolean;
  currentTime: number;
  duration: number;
  onClose: () => void;
  onPlayPause: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  onSeek: (time: number) => void;
}

function formatTime(time?: number) {
  const value = typeof time === "number" && Number.isFinite(time) ? time : 0;
  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60);
  return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
}

export function FullscreenPlayerDrawer({
  isOpen,
  music,
  isPlaying,
  lyrics,
  lyricLoading = false,
  currentTime,
  duration,
  onClose,
  onPlayPause,
  onPrev,
  onNext,
  onSeek,
}: FullscreenPlayerDrawerProps) {
  const [mobilePanel, setMobilePanel] = useState<"cover" | "lyrics">("cover");

  const activeIndex = useMemo(() => {
    if (lyrics.length === 0) return -1;
    let index = 0;
    for (let i = 0; i < lyrics.length; i += 1) {
      if (lyrics[i].time <= currentTime + 0.2) {
        index = i;
      } else {
        break;
      }
    }
    return index;
  }, [currentTime, lyrics]);

  const activeLineRef = useRef<HTMLDivElement | null>(null);
  const lyricScrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    const scroller = lyricScrollRef.current;
    const activeLine = activeLineRef.current;
    if (!scroller || !activeLine) return;

    const targetTop = activeLine.offsetTop - scroller.clientHeight / 2 + activeLine.clientHeight / 2;
    scroller.scrollTo({ top: Math.max(0, targetTop), behavior: "smooth" });
  }, [activeIndex, isOpen, mobilePanel]);

  useEffect(() => {
    if (!isOpen) return;
    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
    };
  }, [isOpen]);

  if (!music) return null;

  return (
    <AnimatePresence>
      {isOpen ? (
        <ConfigProvider
          theme={{
            token: {
              colorPrimary: "#0ea5e9",
            },
          }}
        >
          <motion.div
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 260 }}
            className="fixed inset-0 z-[120] overflow-hidden bg-[#111315] text-white"
          >
            {music.cover ? (
              <Image
                src={music.cover}
                alt=""
                fill
                sizes="100vw"
                className="scale-125 object-cover opacity-70 blur-3xl"
                unoptimized
              />
            ) : null}
            <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(17,19,21,0.76),rgba(17,19,21,0.54)_48%,rgba(17,19,21,0.82))]" />

            <button
              type="button"
              onClick={onClose}
              className="fixed z-[160] flex h-12 w-12 cursor-pointer items-center justify-center rounded-full bg-black/35 text-white shadow-lg shadow-black/25 backdrop-blur-xl transition-colors hover:bg-white/18 md:h-11 md:w-11 md:bg-white/10"
              style={{
                top: "max(1rem, env(safe-area-inset-top))",
                right: "max(1rem, env(safe-area-inset-right))",
              }}
              aria-label="关闭播放器"
              title="关闭"
            >
              <X className="h-5 w-5" />
            </button>

            <div className="relative z-10 grid h-full w-full px-6 pb-8 pt-16 md:grid-cols-[minmax(320px,0.88fr)_minmax(420px,1.12fr)] md:gap-10 md:px-16 md:py-14 lg:pl-32 lg:pr-24 xl:pl-40 xl:pr-28">
              <section
                className={cn(
                  "min-h-0 flex-col items-center justify-center md:flex",
                  mobilePanel === "cover" ? "flex" : "hidden"
                )}
                onClick={() => setMobilePanel("lyrics")}
              >
                <div className="pointer-events-none absolute left-[8%] top-1/2 hidden h-[420px] w-[420px] -translate-y-1/2 rounded-full bg-white/12 blur-3xl md:block" />
                <div className="relative aspect-square w-full max-w-[min(360px,72vw)] overflow-hidden rounded-[8px] bg-white/10 shadow-2xl shadow-black/35 md:max-w-[360px]">
                  {music.cover ? (
                    <Image
                      src={music.cover}
                      alt={music.title}
                      fill
                      sizes="(max-width: 768px) 70vw, 360px"
                      className="object-cover"
                      unoptimized
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-[#005faa] text-7xl font-bold">
                      {music.title[0]}
                    </div>
                  )}
                </div>

                <div className="mt-6 w-full max-w-[520px] text-center md:mt-6">
                  <h2 className="truncate text-3xl font-semibold leading-tight md:text-4xl">{music.title}</h2>
                  <p className="mt-2 truncate text-base text-white/72 md:text-lg">{music.artist}</p>
                  {music.album ? <p className="mt-1 truncate text-sm text-white/46">{music.album}</p> : null}
                </div>

                <div className="mt-7 w-full max-w-[520px]" onClick={(event) => event.stopPropagation()}>
                  <div className="flex items-center justify-center gap-5">
                    <button
                      type="button"
                      onClick={onPrev}
                      disabled={!onPrev}
                      className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full bg-white/10 text-white/82 backdrop-blur-xl transition-colors hover:bg-white/18 disabled:cursor-not-allowed disabled:opacity-35"
                      title="上一首"
                    >
                      <SkipBack className="h-5 w-5" />
                    </button>
                    <button
                      type="button"
                      onClick={onPlayPause}
                      className="flex h-14 w-14 cursor-pointer items-center justify-center rounded-full bg-white text-[#111315] shadow-lg shadow-black/25 transition-transform active:scale-95"
                      title={isPlaying ? "暂停" : "播放"}
                    >
                      {isPlaying ? <Pause className="h-6 w-6 fill-current" /> : <Play className="ml-0.5 h-6 w-6 fill-current" />}
                    </button>
                    <button
                      type="button"
                      onClick={onNext}
                      disabled={!onNext}
                      className="flex h-11 w-11 cursor-pointer items-center justify-center rounded-full bg-white/10 text-white/82 backdrop-blur-xl transition-colors hover:bg-white/18 disabled:cursor-not-allowed disabled:opacity-35"
                      title="下一首"
                    >
                      <SkipForward className="h-5 w-5" />
                    </button>
                  </div>
                  <div className="mt-5">
                    <Slider
                      min={0}
                      max={duration || 100}
                      value={currentTime}
                      onChange={onSeek}
                      tooltip={{ formatter: formatTime }}
                      styles={{
                        track: { background: "#ffffff" },
                        rail: { background: "rgba(255,255,255,0.22)" },
                        handle: { borderColor: "#ffffff" },
                      }}
                    />
                    <div className="flex justify-between px-1 text-xs font-medium tabular-nums text-white/58">
                      <span>{formatTime(currentTime)}</span>
                      <span>{formatTime(duration)}</span>
                    </div>
                  </div>
                </div>
              </section>

              <section
                className={cn(
                  "min-h-0 overflow-hidden md:block md:pl-8 lg:pl-14",
                  mobilePanel === "lyrics" ? "block" : "hidden"
                )}
                onClick={() => setMobilePanel("cover")}
              >
                <div
                  ref={lyricScrollRef}
                  className="h-full overflow-y-auto overscroll-contain py-[28vh] text-center [&::-webkit-scrollbar]:hidden [&::-webkit-scrollbar]:h-0 [&::-webkit-scrollbar]:w-0"
                  style={{
                    scrollbarWidth: "none",
                    msOverflowStyle: "none",
                  } as CSSProperties & { msOverflowStyle: string }}
                >
                  {lyricLoading ? (
                    <div className="text-xl font-medium text-white/55">歌词加载中...</div>
                  ) : lyrics.length > 0 ? (
                    <div className="mx-auto max-w-3xl space-y-5">
                      {lyrics.map((line, index) => {
                        const active = index === activeIndex;
                        return (
                          <div
                            key={`${line.time}-${index}`}
                            ref={active ? activeLineRef : undefined}
                            className={cn(
                              "text-center text-xl font-semibold leading-9 text-white/42 transition-all duration-300 md:text-2xl md:leading-10",
                              active && "scale-105 text-3xl text-white md:text-4xl md:leading-[3.25rem]"
                            )}
                          >
                            {line.text}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-xl font-medium text-white/55">暂无歌词</div>
                  )}
                </div>
              </section>
            </div>
          </motion.div>
        </ConfigProvider>
      ) : null}
    </AnimatePresence>
  );
}
