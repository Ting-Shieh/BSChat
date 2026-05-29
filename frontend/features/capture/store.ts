"use client";

import { create } from "zustand";
import type { CaptureThumbnail } from "@/shared/types/capture";

interface CaptureState {
  sessionId: string | null;
  thumbnails: CaptureThumbnail[];
  setSessionId: (id: string | null) => void;
  addThumbnail: (thumb: CaptureThumbnail) => void;
  updateThumbnail: (localUrl: string, patch: Partial<CaptureThumbnail>) => void;
  clear: () => void;
}

export const useCaptureStore = create<CaptureState>((set) => ({
  sessionId: null,
  thumbnails: [],
  setSessionId: (id) => set({ sessionId: id }),
  addThumbnail: (thumb) => set((s) => ({ thumbnails: [...s.thumbnails, thumb] })),
  updateThumbnail: (localUrl, patch) =>
    set((s) => ({
      thumbnails: s.thumbnails.map((t) => (t.localUrl === localUrl ? { ...t, ...patch } : t)),
    })),
  clear: () => set({ sessionId: null, thumbnails: [] }),
}));
