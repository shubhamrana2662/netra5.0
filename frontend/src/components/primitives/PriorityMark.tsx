import type { Priority } from "../../data/types";
import s from "./primitives.module.css";

const LABEL = { CRITICAL: "Critical", HIGH: "High priority", MEDIUM: "Medium priority" } as const;

export function PriorityMark({ priority }: { priority: Priority }) {
  if (!priority) return null;
  const cls = priority === "MEDIUM" ? s.medium : priority === "CRITICAL" ? s.critical : s.high;
  return <span className={`${s.pm} ${cls}`}><i />{LABEL[priority]}</span>;
}
