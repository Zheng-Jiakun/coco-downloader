'use client';

import { Drawer } from 'antd';
import { X } from 'lucide-react';

import DeveloperProfile from './developer-profile';

// Mock constants since files are missing
const isDesktop = true;
const TITLE_BAR_HEIGHT = 0;

interface DeveloperPanelProps {
  onClose: () => void;
  open: boolean;
}

export default function DeveloperPanel({ open, onClose }: DeveloperPanelProps) {
  return (
    <Drawer
      closable={false}
      keyboard
      onClose={onClose}
      open={open}
      placement="bottom"
      size={isDesktop ? `calc(100vh - ${TITLE_BAR_HEIGHT}px)` : '100vh'}
      styles={{
        body: {
          padding: 0,
        },
      }}
    >
      <button
        aria-label="关闭开发者面板"
        className="fixed right-4 top-4 z-50 flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-black/10 bg-white/85 text-neutral-700 shadow-sm backdrop-blur transition hover:bg-white dark:border-white/10 dark:bg-neutral-900/85 dark:text-neutral-200 dark:hover:bg-neutral-800"
        onClick={onClose}
        type="button"
      >
        <X size={18} />
      </button>
      <DeveloperProfile />
    </Drawer>
  );
}
