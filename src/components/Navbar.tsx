'use client';

import Link from "next/link";
import Image from "next/image";
import { Download, Github, Sun, Moon, Heart, ShieldCheck } from "lucide-react";
import { useState, MouseEvent, useEffect } from "react";
import { useTheme } from "next-themes";
import DeveloperPanel from "./DeveloperPanel";
import { DonationModal } from "./DonationModal";

export function Navbar() {
  const [showDevPanel, setShowDevPanel] = useState(false);
  const [showDonation, setShowDonation] = useState(false);
  const { theme, setTheme, resolvedTheme } = useTheme();
  const currentTheme = resolvedTheme ?? theme ?? "light";
  const [autoSystem, setAutoSystem] = useState(true);

  const toggleTheme = (event: MouseEvent<HTMLButtonElement>) => {
    const isDark = currentTheme === 'dark';
    const newTheme = isDark ? 'light' : 'dark';

    // Check if View Transitions API is supported
    if (!document.startViewTransition) {
      setTheme(newTheme);
      return;
    }

    const x = event.clientX;
    const y = event.clientY;
    const endRadius = Math.hypot(
      Math.max(x, innerWidth - x),
      Math.max(y, innerHeight - y)
    );

    const transition = document.startViewTransition(() => {
      setTheme(newTheme);
    });

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`,
      ];

      document.documentElement.animate(
        {
          clipPath: clipPath,
        },
        {
          duration: 500,
          easing: "ease-in",
          pseudoElement: "::view-transition-new(root)",
        }
      );
    });
  };

  useEffect(() => {
    try {
      const raw = localStorage.getItem('coco:autoTheme');
      const enabled = raw !== '0';
      setAutoSystem(enabled);
      if (enabled) {
        setTheme('system');
      }
    } catch (e) {
      // ignore
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const toggleAutoSystem = () => {
    const next = !autoSystem;
    setAutoSystem(next);
    try {
      localStorage.setItem('coco:autoTheme', next ? '1' : '0');
    } catch (e) {}

    if (next) {
      setTheme('system');
    } else {
      // lock to current resolved theme (or default to light)
      setTheme(resolvedTheme ?? theme ?? 'light');
    }
  };

  return (
    <>
      <nav className="h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-sky-100 dark:border-slate-800 z-50 px-4 md:px-8 flex items-center justify-between transition-colors duration-300">
        <Link href="/" className="group flex items-center gap-3">
          <Image src="/images/coco-downloader.svg" alt="CoCo Downloader" width={40} height={40} className="h-10 w-10 transition-transform group-hover:scale-105" />
          <span className="hidden text-xl font-bold tracking-normal text-[#005faa] dark:text-[#a3c9ff] sm:inline">
            CoCo Downloader
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <a
            href="https://github.com/markcxx/coco-downloader/releases"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex cursor-pointer items-center gap-2 rounded-full bg-[#005faa] px-3 py-2 text-sm font-medium text-white transition-all duration-300 hover:bg-[#0078d4] dark:bg-[#a3c9ff] dark:text-[#001c39] dark:hover:bg-[#d3e3ff]"
            title="下载客户端"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">下载客户端</span>
          </a>

          <button
            onClick={() => setShowDonation(true)}
            className="p-2 text-slate-400 dark:text-slate-500 hover:text-rose-500 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-900/20 rounded-full transition-all duration-300 cursor-pointer"
            title="支持作者"
          >
            <Heart className="w-5 h-5" />
          </button>

          <a
            href="https://github.com/markcxx/coco-downloader"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 text-slate-400 dark:text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-all duration-300 cursor-pointer"
          >
            <Github className="w-5 h-5" />
          </a>

          <button
            onClick={toggleTheme}
            className="cursor-pointer rounded-full p-2 text-slate-500 transition-all duration-300 hover:bg-sky-50 hover:text-sky-600 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-sky-300"
            aria-label="Toggle theme"
          >
            {currentTheme === 'dark' ? (
              <Sun className="w-5 h-5" />
            ) : (
              <Moon className="w-5 h-5" />
            )}
          </button>
          <button
            onClick={toggleAutoSystem}
            className={"p-2 ml-1 rounded-full transition-all duration-300 cursor-pointer " + (autoSystem ? 'bg-sky-50 text-sky-600 dark:bg-sky-900/10' : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800')}
            title={autoSystem ? '自动主题已开启' : '自动主题已关闭'}
            aria-pressed={!autoSystem}
          >
            <ShieldCheck className={"w-5 h-5 " + (autoSystem ? 'text-sky-600' : '')} />
          </button>
        </div>
      </nav>

      <DeveloperPanel open={showDevPanel} onClose={() => setShowDevPanel(false)} />
      <DonationModal isOpen={showDonation} onClose={() => setShowDonation(false)} />
    </>
  );
}
