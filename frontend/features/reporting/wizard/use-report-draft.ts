"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { emptyDraft, hasContent, type ReportDraft } from "../draft";
import { type DraftStore, openDraftStore } from "../draft-store";

const SAVE_DELAY_MS = 400;

/** The report being written, kept on the device as the person types. */
export function useReportDraft() {
  const [draft, setDraft] = useState<ReportDraft | null>(null);
  const [restored, setRestored] = useState(false);
  const [persistent, setPersistent] = useState(true);
  const store = useRef<DraftStore | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef<ReportDraft | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const opened = await openDraftStore();
      const saved = await opened.load().catch(() => null);
      if (cancelled) return;
      store.current = opened;
      setPersistent(opened.persistent);
      const initial = saved && hasContent(saved) ? saved : emptyDraft();
      setRestored(Boolean(saved && hasContent(saved)));
      latest.current = initial;
      setDraft(initial);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const flush = useCallback(async () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    if (store.current && latest.current) await store.current.save(latest.current);
  }, []);

  // Save immediately if the page is being hidden or closed.
  useEffect(() => {
    const onHide = () => void flush();
    window.addEventListener("pagehide", onHide);
    document.addEventListener("visibilitychange", onHide);
    return () => {
      window.removeEventListener("pagehide", onHide);
      document.removeEventListener("visibilitychange", onHide);
      void flush();
    };
  }, [flush]);

  const update = useCallback(
    (patch: Partial<ReportDraft>, { immediate = false } = {}) => {
      setDraft((current) => {
        if (!current) return current;
        const next = { ...current, ...patch, updatedAt: new Date().toISOString() };
        latest.current = next;
        return next;
      });
      if (timer.current) clearTimeout(timer.current);
      if (immediate) void Promise.resolve().then(flush);
      else timer.current = setTimeout(() => void flush(), SAVE_DELAY_MS);
    },
    [flush],
  );

  /** Replace the whole draft (used by submission) and save it now. */
  const replace = useCallback(
    async (next: ReportDraft) => {
      latest.current = next;
      setDraft(next);
      await flush();
    },
    [flush],
  );

  const discard = useCallback(async () => {
    if (timer.current) clearTimeout(timer.current);
    await store.current?.clear();
    const fresh = emptyDraft();
    latest.current = fresh;
    setDraft(fresh);
    setRestored(false);
  }, []);

  return { draft, restored, persistent, update, replace, discard };
}
