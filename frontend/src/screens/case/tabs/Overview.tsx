import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Case } from "../../../data/types";
import { eventsForCase } from "../../../data/corpus";
import { useLiveStore } from "../../../state/useLiveStore";
import { Button } from "../../../components/primitives/Button";
import { CaseNotesSection } from "../../../components/notes/CaseNotesSection";
import s from "../../../components/case/case.module.css";

export function Overview({ caseData }: { caseData: Case }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-8, 32px)" }}>
      <div className={s.ovGrid}>
        <div>
          <div className="t-label">Case brief</div>
          <p className={`t-body-lg measure ${!expanded ? s.clamp : ""}`} style={{ marginTop: "var(--space-3)" }}>
            {caseData.brief || "No brief filed yet."}
          </p>
          {caseData.brief && caseData.brief.length > 180 && (
            <Button variant="ghost" onClick={() => setExpanded(e => !e)}>
              {expanded ? "Show less" : "Read full brief"}
            </Button>
          )}

          <div className={`t-label ${s.sectGap}`}>Key figures</div>
          <div className="figs">
            <div className="fig"><b>{caseData.entities}</b><span>Entities</span></div>
            <div className="fig"><b>{caseData.evidence}</b><span>Evidence items</span></div>
            <div className="fig"><b>{caseData.leads}</b><span>Active leads</span></div>
          </div>

          <div className={`t-label ${s.sectGap}`}>Latest development</div>
          <p className="t-body measure" style={{ color: "var(--text-secondary)" }}>
            {caseData.latest || "Under active evidence ingestion and topological correlation analysis."}
          </p>
        </div>

        <aside>
          <div className="t-label">Network</div>
          <MiniNetwork onClick={() => navigate(`/investigations/${caseData.id}/network`)} />
          <div className="t-label" style={{ marginTop: "var(--space-8)" }}>Recent timeline</div>
          <MiniTimeline caseId={caseData.id} onOpenTimeline={() => navigate(`/investigations/${caseData.id}/timeline`)} />
        </aside>
      </div>

      {/* Case-specific Investigator Notes & Sticky Wall */}
      <CaseNotesSection caseId={caseData.id} />
    </div>
  );
}

function MiniNetwork({ onClick }: { onClick?: () => void }) {
  return (
    <svg className={s.miniNet} viewBox="0 0 240 130" role="img" aria-label="Network preview" onClick={onClick} style={{ cursor: "pointer" }}>
      <line className={s.miniEdge} x1="30" y1="40" x2="90" y2="30" />
      <line className={s.miniEdge} x1="90" y1="30" x2="160" y2="70" />
      <line className={s.miniEdge} x1="90" y1="30" x2="120" y2="105" />
      <line className={s.miniEdge} x1="160" y1="70" x2="210" y2="60" />
      <circle className={s.miniNode} cx="30" cy="40" r="3.5" />
      <circle className={s.miniNodeSel} cx="90" cy="30" r="4.5" />
      <circle className={s.miniNode} cx="160" cy="70" r="3.5" />
      <circle className={s.miniNode} cx="120" cy="105" r="3.5" />
      <circle className={s.miniNode} cx="210" cy="60" r="3.5" />
    </svg>
  );
}

function MiniTimeline({ caseId, onOpenTimeline }: { caseId: string; onOpenTimeline: () => void }) {
  const { activeTimeline } = useLiveStore();
  const isDemo = caseId === "CYB-2026-042" || caseId === "demo-shadowlink";
  const rawEvs = (activeTimeline && activeTimeline.length > 0)
    ? activeTimeline
    : (isDemo ? (eventsForCase(caseId) || []) : []);
  const evs = rawEvs.slice(0, 4);

  if (evs.length === 0) {
    return (
      <div style={{ padding: "var(--space-3) 0", color: "var(--text-muted)", fontSize: "13px" }}>
        No timeline events recorded yet. Ingest evidence to reconstruct chronological activity.
      </div>
    );
  }

  return (
    <div>
      <ul className={s.evList}>
        {evs.map(ev => {
          const lbl = ev.label || "Event recorded";
          return (
            <li key={ev.id || Math.random().toString()} className={s.evRow}>
              <span className={s.evTs}>{ev.ts || "—"}</span>
              <span className={s.evLabel}>{lbl.length > 35 ? `${lbl.slice(0, 32)}…` : lbl}</span>
            </li>
          );
        })}
      </ul>
      <Button variant="ghost" icon="arrow" onClick={onOpenTimeline} style={{ marginTop: "var(--space-3)" }}>
        View full chronology
      </Button>
    </div>
  );
}
