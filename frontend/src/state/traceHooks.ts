import { useEffect, useState, type RefObject } from "react";
import { TraceStore, type TraceRecord } from "./TraceStore";

export function useTrace(id: string): TraceRecord {
  const [rec, setRec] = useState<TraceRecord>(() => TraceStore.get(id));
  useEffect(() => {
    setRec(TraceStore.get(id));
    return TraceStore.subscribe((tid, r) => { if (tid === id) setRec({ ...r }); });
  }, [id]);
  return rec;
}

/** Marks SEEN after 800ms of ≥60% viewport dwell (IntersectionObserver). */
export function useTraceDwell(ref: RefObject<HTMLElement | null>, id: string): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let timer: number | undefined;
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) timer = window.setTimeout(() => TraceStore.markSeen(id), 800);
        else window.clearTimeout(timer);
      },
      { threshold: 0.6 },
    );
    io.observe(el);
    return () => { io.disconnect(); window.clearTimeout(timer); };
  }, [ref, id]);
}
