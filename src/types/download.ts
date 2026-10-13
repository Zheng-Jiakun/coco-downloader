import { MusicItem } from "./music";

export type DownloadStatus = 'pending' | 'downloading' | 'completed' | 'error';

export interface DownloadTask {
  id: string; // unique task id (e.g. musicId + timestamp)
  musicItem: MusicItem;
  status: DownloadStatus;
  progress: number; // 0 to 100
  fileName: string;
  convertAacToMp3: boolean;
  saveToNas: boolean;
  error?: string;
  startTime: number;
}
