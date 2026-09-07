import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { eventsForCase, evidenceLabel, entityById } from "../../../data/corpus";
import { TraceChip } from "../../../components/primitives/TraceChip";
import { useLiveStore } from "../../../state/useLiveStore";
import s from "../../../components/case/case.module.css";

import { Button } from "../../../components/primitives/Button";

const EVENT_KINDS = ["ALL", "COMMUNICATION", "TRANSACTION", "LOCATION", "DEVICE"] as const;

export function TimelineTab({ caseId, onOpenEvidence }: { caseId: string; onOpenEvidence: () => void }) {
  const { activeTimeline, activeCase } = useLiveStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const [kindFilter, setKindFilter] = useState<typeof EVENT_KINDS[number]>("ALL");
  const entityParam = searchParams.get("entity");

  const isDemo = caseId === "CYB-2026-042" || caseId === "demo-shadowlink" || activeCase?.id === "CYB-2026-042";
  const evts = (activeTimeline && activeTimeline.length > 0)
    ? activeTimeline
    : (isDemo ? eventsForCase(caseId) : []);

  const filtered = evts.filter(e => {
    if (kindFilter !== "ALL" && e.kind !== kindFilter) return false;
    if (entityParam && !e.entityIds.includes(entityParam)) return false;
    return true;
  });

  return (
    <div>
      <div className="t-label" style={{ marginBottom: "var(--space-2)" }}>
        Reconstructed sequence of events ({evts.length} events logged)
      </div>
      <p className="t-body measure" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
        Temporal reconciliation across cell towers, WhatsApp extractions, and financial telemetry.
      </p>

      <div style={{ display: "flex", gap: "var(--space-2)", marginBottom: "var(--space-8)", flexWrap: "wrap", alignItems: "center" }}>
        {EVENT_KINDS.map(k => (
          <button
            key={k}
            className={`${s.evPill} ${kindFilter === k ? s.evPillOn : ""}`}
            onClick={() => setKindFilter(k)}
          >
            {k}
          </button>
        ))}
        {entityParam && (
          <button
            className={`${s.evPill} ${s.evPillOn}`}
            style={{ color: "var(--intel)", borderColor: "var(--intel)" }}
            onClick={() => {
              const next = new URLSearchParams(searchParams);
              next.delete("entity");
              setSearchParams(next, { replace: true });
            }}
          >
            ENTITY: {entityById.get(entityParam)?.name || entityParam} ✕
          </button>
        )}
      </div>

      {evts.length === 0 ? (
        <div style={{
          padding: "var(--space-12) var(--space-6)", textAlign: "center",
          background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
          borderRadius: "var(--radius-card)", marginTop: "var(--space-4)"
        }}>
          <div style={{ font: "var(--type-mono-xs)", color: "var(--intel)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
            Chronological Forensics
          </div>
          <h3 style={{ font: "var(--type-title-3)", color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
            Timeline Sequence Not Yet Established
          </h3>
          <p className="measure" style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", margin: "0 auto var(--space-6) auto" }}>
            Reconstructed timelines across call logs, messaging timestamps, bank transactions, and cell tower telemetry will appear automatically once evidence is ingested.
          </p>
          <Button variant="primary" icon="plus" onClick={onOpenEvidence}>
            Ingest Evidence to Build Timeline
          </Button>
        </div>
      ) : filtered.length === 0 ? (
        <div style={{
          padding: "var(--space-8) var(--space-4)", textAlign: "center",
          background: "var(--surface-1)", border: "1px solid var(--line)",
          borderRadius: "var(--radius-card)", marginTop: "var(--space-4)"
        }}>
          <p style={{ color: "var(--text-secondary)", font: "var(--type-body)", marginBottom: "var(--space-4)" }}>
            No events match the selected category filter: <b>{kindFilter}</b>
          </p>
          <Button variant="secondary" onClick={() => setKindFilter("ALL")}>
            Show All Events
          </Button>
        </div>
      ) : (
        <div className={s.timelineTrack}>
          <div className={s.timelineLine} />
          {filtered.map(ev => (
            <div key={ev.id} className={s.tlNode}>
              <span className={s.tlDot} />
              <div className={s.tlTime}>{ev.date} · {ev.ts} · {ev.kind}</div>
              <div className={s.tlTitle}>{ev.label}</div>
              {ev.entityIds.length > 0 && (
                <div className={s.tlMeta}>
                  Entities: {ev.entityIds.map(eid => entityById.get(eid)?.name ?? eid).join(", ")}
                </div>
              )}
              {ev.evidenceIds.length > 0 && (
                <div style={{ display: "flex", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                  {ev.evidenceIds.map(eid => (
                    <TraceChip key={eid} label={evidenceLabel(eid)} onClick={onOpenEvidence} />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
