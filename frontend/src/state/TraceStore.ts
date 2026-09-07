export type TraceState = "NEW" | "SEEN" | "RELATED" | "REVISITED";

export interface TraceRecord {
  id: string;
  state: TraceState;
  surfacedIn: string[];
  lastSeenAt?: number;
}

const KEY = "cd-trace-v1";
type Listener = (id: string, rec: TraceRecord) => void;

class TraceStoreImpl {
  private records = new Map<string, TraceRecord>();
  private listeners = new Set<Listener>();

  constructor() {
    try {
      const raw = typeof window !== "undefined" ? sessionStorage.getItem(KEY) : null;
      if (raw) {
        for (const [id, rec] of Object.entries(JSON.parse(raw) as Record<string, TraceRecord>)) {
          this.records.set(id, rec);
        }
      }
    } catch { /* storage unavailable — session-only memory */ }
    // Amendment B seed: finding fnd-01 surfaces CDR Record 18.
    if (!this.records.has("evd-cdr-18")) this.markRelated("evd-cdr-18", "fnd-01");
  }

  get(id: string): TraceRecord {
    return this.records.get(id) ?? { id, state: "NEW", surfacedIn: [] };
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => { this.listeners.delete(fn); };
  }

  /** NEW→SEEN on first 800ms dwell; SEEN→REVISITED on return. Silent. */
  markSeen(id: string): void {
    const r = this.get(id);
    if (r.state === "NEW") this.set(id, { state: "SEEN", lastSeenAt: Date.now() });
    else if (r.state === "SEEN") this.set(id, { state: "REVISITED", lastSeenAt: Date.now() });
  }

  markRelated(id: string, findingId: string): void {
    const r = this.get(id);
    this.set(id, {
      state: r.state === "NEW" ? "RELATED" : r.state,
      surfacedIn: [...new Set([...r.surfacedIn, findingId])],
    });
  }

  private set(id: string, patch: Partial<TraceRecord>): void {
    const next: TraceRecord = { ...this.get(id), ...patch, id };
    this.records.set(id, next);
    try {
      if (typeof window !== "undefined") {
        sessionStorage.setItem(KEY, JSON.stringify(Object.fromEntries(this.records)));
      }
    } catch { /* ignore */ }
    this.listeners.forEach(fn => fn(id, next));
  }
}

export const TraceStore = new TraceStoreImpl();
