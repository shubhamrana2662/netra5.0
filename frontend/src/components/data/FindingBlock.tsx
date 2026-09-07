import { TraceChip } from "../primitives/TraceChip";
import { evidenceLabel } from "../../data/corpus";
import type { Finding } from "../../data/types";
import s from "./finding.module.css";

export function FindingBlock({ finding, onOpenEvidence }: { finding: Finding; onOpenEvidence: () => void }) {
  return (
    <div className={s.fb}>
      <div className="t-label">Key finding</div>
      <p className={`t-body-lg measure ${s.body}`}>{finding.body}</p>
      <div className={s.conf}>Confidence {finding.confidence}</div>
      <div className="t-label" style={{ marginTop: "var(--space-6)" }}>Evidence</div>
      <div className={s.chips}>
        {finding.evidenceIds.map(id => (
          <TraceChip key={id} label={evidenceLabel(id)} onClick={onOpenEvidence} />
        ))}
      </div>
    </div>
  );
}
