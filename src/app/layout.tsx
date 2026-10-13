import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ErrorNotifications } from "@/components/ErrorNotifications";

export const metadata: Metadata = {
  title: "COCO音乐下载站",
  description: "简约纯净的音乐下载工具",
  icons: {
    icon: "/logo.svg",
  },
};

export const dynamic = "force-dynamic";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const downloadEnabled = process.env.ENABLE_DOWNLOAD !== "0";
  const musicLibraryRoot =
    process.env.MUSIC_LIBRARY_DIR?.trim() ||
    process.env.NAS_MUSIC_DIR?.trim() ||
    process.env.DOWNLOAD_TARGET_DIR?.trim() ||
    "";
  const saveToNasSupported = Boolean(musicLibraryRoot) && (process.env.SAVE_TO_NAS ?? "1") !== "0";
  const announcementEnabled =
    !downloadEnabled && (process.env.ANNOUNCEMENT_ENABLED ?? "1") === "1";
  const announcementText =
    process.env.ANNOUNCEMENT_TEXT ??
    "由于本站当前流量包达到上限，下载功能已临时关闭，将为你跳转到原链接。";
  const clientEnv = {
    ENABLE_DOWNLOAD: downloadEnabled ? "1" : "0",
    SAVE_TO_NAS_SUPPORTED: saveToNasSupported ? "1" : "0",
    ANNOUNCEMENT_ENABLED: announcementEnabled ? "1" : "0",
    ANNOUNCEMENT_TEXT: announcementText,
  };

  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="antialiased bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <script
            dangerouslySetInnerHTML={{
              __html: `window.__COCO_ENV=${JSON.stringify(clientEnv)};`,
            }}
          />
          <div className="sticky top-0 z-[60] w-full flex flex-col">
            {announcementEnabled ? (
              <div className="w-full bg-orange-50/90 dark:bg-orange-950/90 border-b border-orange-100 dark:border-orange-900 px-4 py-2 text-center text-xs sm:text-sm text-orange-800 dark:text-orange-200 flex flex-wrap items-center justify-center gap-1 backdrop-blur-sm transition-colors duration-300">
                <span>{announcementText}</span>
              </div>
            ) : null}
            <Navbar />
          </div>
          <div className="min-h-screen">{children}</div>
          <ErrorNotifications />
        </ThemeProvider>
      </body>
    </html>
  );
}
