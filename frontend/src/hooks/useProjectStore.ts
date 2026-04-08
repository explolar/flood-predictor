/**
 * Lightweight client-side project persistence using localStorage.
 * Stores saved AOIs, run history, and named projects.
 */

import { useState, useCallback, useEffect } from "react";

const STORAGE_KEY = "fluviaai_projects";
const HISTORY_KEY = "fluviaai_run_history";

export interface SavedAOI {
  id: string;
  name: string;
  geojson: GeoJSON.Geometry;
  center: [number, number];
  created_at: string;
}

export interface RunRecord {
  id: string;
  aoi_id: string;
  tab: string;
  params: Record<string, any>;
  result_snapshot: Record<string, any>;
  timestamp: string;
}

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveToStorage(key: string, value: any): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Silently fail if storage is full
  }
}

export function useProjectStore() {
  const [savedAOIs, setSavedAOIs] = useState<SavedAOI[]>(() => loadFromStorage(STORAGE_KEY, []));
  const [runHistory, setRunHistory] = useState<RunRecord[]>(() => loadFromStorage(HISTORY_KEY, []));

  // Persist on change
  useEffect(() => { saveToStorage(STORAGE_KEY, savedAOIs); }, [savedAOIs]);
  useEffect(() => { saveToStorage(HISTORY_KEY, runHistory); }, [runHistory]);

  const saveAOI = useCallback((name: string, geojson: GeoJSON.Geometry, center: [number, number]) => {
    const aoi: SavedAOI = {
      id: generateId(),
      name,
      geojson,
      center,
      created_at: new Date().toISOString(),
    };
    setSavedAOIs((prev) => [aoi, ...prev]);
    return aoi;
  }, []);

  const deleteAOI = useCallback((id: string) => {
    setSavedAOIs((prev) => prev.filter((a) => a.id !== id));
    setRunHistory((prev) => prev.filter((r) => r.aoi_id !== id));
  }, []);

  const addRun = useCallback((aoiId: string, tab: string, params: Record<string, any>, resultSnapshot: Record<string, any>) => {
    const record: RunRecord = {
      id: generateId(),
      aoi_id: aoiId,
      tab,
      params,
      result_snapshot: resultSnapshot,
      timestamp: new Date().toISOString(),
    };
    // Keep max 100 records
    setRunHistory((prev) => [record, ...prev].slice(0, 100));
    return record;
  }, []);

  const getRunsForAOI = useCallback((aoiId: string) => {
    return runHistory.filter((r) => r.aoi_id === aoiId);
  }, [runHistory]);

  const clearHistory = useCallback(() => {
    setRunHistory([]);
  }, []);

  return {
    savedAOIs,
    runHistory,
    saveAOI,
    deleteAOI,
    addRun,
    getRunsForAOI,
    clearHistory,
  };
}
