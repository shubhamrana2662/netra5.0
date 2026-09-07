import { useState } from "react";
import { entities as fallbackEntities } from "../../../data/entities";
import type { Entity } from "../../../data/types";
import { Icon } from "../../../components/icons";
import { TraceChip } from "../../../components/primitives/TraceChip";
import { evidenceLabel } from "../../../data/corpus";
import { useLiveStore } from "../../../state/useLiveStore";
import s from "../../../components/case/case.module.css";

import { Button } from "../../../components/primitives/Button";

export function EntitiesTab({ onOpenEvidence }: { onOpenEvidence: () => void }) {
  const { activeGraph, activeCase } = useLiveStore();
  const [selected, setSelected] = useState<Entity | null>(null);

  const isDemo = activeCase?.id === "CYB-2026-042" || activeCase?.id === "demo-shadowlink";
  const displayedEntities = (activeGraph?.entities && activeGraph.entities.length > 0)
    ? activeGraph.entities
    : (isDemo ? fallbackEntities : []);

  return (
    <div>
      <div className="t-label" style={{ marginBottom: "var(--space-4)" }}>
        Identified targets & entities ({displayedEntities.length})
      </div>

      {displayedEntities.length === 0 ? (
        <div style={{
          padding: "var(--space-12) var(--space-6)", textAlign: "center",
          background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
          borderRadius: "var(--radius-card)", marginTop: "var(--space-4)"
        }}>
          <div style={{ font: "var(--type-mono-xs)", color: "var(--intel)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
            Entity Intelligence Pipeline
          </div>
          <h3 style={{ font: "var(--type-title-3)", color: "var(--text-primary)", marginBottom: "var(--space-2)" }}>
            No Entities Identified Yet
          </h3>
          <p className="measure" style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", margin: "0 auto var(--space-6) auto" }}>
            Entities (suspect persons, phone numbers, bank accounts, UPI VPAs, and devices) are automatically extracted when evidence files are ingested and analyzed by the AI HingBERT NER & graph engine.
          </p>
          <Button variant="primary" icon="plus" onClick={onOpenEvidence}>
            Ingest Evidence to Extract Entities
          </Button>
        </div>
      ) : (
        <div className={s.entityGrid}>
          {displayedEntities.map(e => (
            <div key={e.id} className={s.entityCard} onClick={() => setSelected(e)} style={{ cursor: "pointer" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-2)" }}>
                <span className="t-mono-xs" style={{ color: "var(--text-muted)" }}>{e.kind} · {e.id}</span>
                {e.risk && <span className={`${s.riskBadge} ${s[`risk${e.risk}`]}`}>{e.risk} RISK</span>}
              </div>
              <div style={{ font: "500 16px var(--font-sans)", color: "var(--text-primary)", marginBottom: "var(--space-1)" }}>
                {e.name}
              </div>
              <div style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
                {e.meta}
              </div>
              <div style={{ font: "var(--type-mono-xs)", color: "var(--text-muted)" }}>
                {e.mentionCount ?? 1} occurrences across case records
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <>
          <div className={s.sheetOverlay} onClick={() => setSelected(null)} />
          <div className={s.sheet}>
            <div className={s.sheetHead}>
              <span className="t-label">{selected.kind} PROFILE</span>
              <button className={s.sheetClose} onClick={() => setSelected(null)} aria-label="Close profile">
                <Icon name="close" size={18} />
              </button>
            </div>
            <h2 className="t-title-2" style={{ marginBottom: "var(--space-2)" }}>{selected.name}</h2>
            <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center", marginBottom: "var(--space-6)" }}>
              <span className="t-mono-xs" style={{ color: "var(--text-muted)" }}>ID: {selected.id}</span>
              {selected.risk && <span className={`${s.riskBadge} ${s[`risk${selected.risk}`]}`}>{selected.risk} RISK</span>}
            </div>

            <div className="t-label" style={{ marginBottom: "var(--space-2)" }}>Telemetry & metadata</div>
            <p className="t-body measure" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-6)" }}>
              {selected.meta}. Correlated by AI NER extraction engine across communication and transaction records.
            </p>

            <div className="t-label" style={{ marginBottom: "var(--space-2)" }}>Linked evidence artifacts</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
              {(selected.linkedEvidenceIds && selected.linkedEvidenceIds.length > 0) ? (
                selected.linkedEvidenceIds.map(id => (
                  <TraceChip key={id} label={evidenceLabel(id)} onClick={onOpenEvidence} />
                ))
              ) : (
                <span className="t-body-sm" style={{ color: "var(--text-muted)" }}>Direct observation in case records</span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
