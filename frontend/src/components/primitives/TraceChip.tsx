import { useRef } from "react";
import { useTrace, useTraceDwell } from "../../state/traceHooks";
import { TraceDot } from "./TraceDot";
import s from "./primitives.module.css";

const NOTE: Partial<Record<string, string>> = {
  RELATED: "Related to your finding",
  REVISITED: "Revisited",
};

export function TraceChip({ label, onClick }: { label: string; onClick?: () => void }) {
  const ref = useRef<HTMLButtonElement>(null);
  const rec = useTrace(label);
  useTraceDwell(ref, label);
  return (
    <button ref={ref} className={s.chip} onClick={onClick}>
      <TraceDot state={rec.state} />
      {label}
      {NOTE[rec.state] && <span className={s.note}>{NOTE[rec.state]}</span>}
    </button>
  );
}
