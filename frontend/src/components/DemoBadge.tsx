import type { CSSProperties } from "react";
import type { Case } from "../data/types";

/**
 * Persistent marker for the synthetic demonstration dataset.
 *
 * Rendered anywhere a SYNTHETIC_DEMO case is shown so that no screenshot can be
 * mistaken for a real investigation. Visibility must be driven off
 * `source_type === "SYNTHETIC_DEMO"` — never off styling alone.
 */
export function DemoBadge({ size = "md", style }: { size?: "sm" | "md"; style?: CSSProperties }) {
  const pad = size === "sm" ? "2px 8px" : "4px 10px";
  const fontSize = size === "sm" ? 9.5 : 11;
  const dot = size === "sm" ? 4 : 5;
  return (
    <span
      role="note"
      aria-label="Synthetic demonstration dataset — not a real investigation"
      title="Synthetic demonstration dataset — not a real investigation"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: pad,
        borderRadius: "var(--radius-pill)",
        background: "var(--warning-tint)",
        border: "1px solid rgba(230, 168, 74, 0.5)",
        color: "var(--warning)",
        fontFamily: "var(--font-mono)",
        fontSize,
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        lineHeight: 1.2,
        ...style,
      }}
    >
      <span style={{ width: dot, height: dot, borderRadius: "50%", background: "var(--warning)", display: "inline-block", flex: "none" }} />
      Demonstration · Synthetic Dataset
    </span>
  );
}

/** True when a case is the synthetic demonstration dataset. */
export function isSyntheticDemo(c?: Case | null): boolean {
  return !!c && c.source_type === "SYNTHETIC_DEMO";
}
