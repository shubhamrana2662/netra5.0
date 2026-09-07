import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Block, staggerContainer, staggerItem } from "../../app/transitions";
import { PriorityMark } from "../../components/primitives/PriorityMark";
import { useLiveStore } from "../../state/useLiveStore";
import s from "./command.module.css";

export function CommandCenter() {
  const navigate = useNavigate();
  const { cases, backendOnline, fetchCases } = useLiveStore();

  useEffect(() => {
    fetchCases();
  }, []);

  const dateStr = new Intl.DateTimeFormat("en-US", {
    weekday: "long", month: "short", day: "numeric", year: "numeric",
  }).format(new Date());

  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning, Officer." : hour < 18 ? "Good afternoon, Officer." : "Good evening, Officer.";

  // Live figures reflect real investigations only — the synthetic demonstration
  // case is excluded so the situation summary never mixes demo data with real counts.
  const liveCases = cases.filter(c => c.source_type !== "SYNTHETIC_DEMO");
  const activeCases = liveCases.filter(c => c.status === "ACTIVE");
  const criticalCases = liveCases.filter(c => c.priority === "CRITICAL" || c.priority === "HIGH");
  const totalEvidence = liveCases.reduce((acc, c) => acc + (c.evidence || 0), 0);
  const totalEntities = liveCases.reduce((acc, c) => acc + (c.entities || 0), 0);

  const situationStats = [
    { label: "Active matters", value: activeCases.length },
    { label: "Critical priority", value: criticalCases.length },
    { label: "Indexed evidence", value: totalEvidence },
    { label: "Correlated entities", value: totalEntities },
  ];

  const topPriorityCases = criticalCases.slice(0, 5);

  // Intelligence feed derived from real case activity — no fabricated events.
  // Each item points at an actual investigation the officer can open.
  const feed = liveCases
    .slice(0, 6)
    .map(c => ({
      id: c.id,
      time: c.updated || "—",
      text: `${c.name} · ${c.evidence || 0} evidence · ${c.entities || 0} entities`,
      to: `/investigations/${c.id}/overview`,
    }));

  return (
    <div className="page">
      <Block>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div>
            <div className={s.dateline}>{dateStr} · {backendOnline ? "LIVE REPOSITORY BRIEFING" : "OFFLINE BRIEFING"}</div>
            <h1 className={`t-title-1 ${s.greeting}`}>{greeting}</h1>
            <p className={`t-body-lg measure ${s.lede}`}>
              {backendOnline
                ? (liveCases.length > 0
                    ? `Live case repository connected · ${liveCases.length} active investigation${liveCases.length === 1 ? "" : "s"}.`
                    : "Live case repository connected · no investigations registered yet.")
                : "Backend unavailable — no live intelligence is being displayed."}
            </p>
          </div>
          <div style={{ display: "flex", gap: "var(--space-3)", marginTop: "var(--space-2)" }}>
            <button
              type="button"
              onClick={() => navigate("/intelligence")}
              style={{
                padding: "8px 16px", borderRadius: "var(--radius-input)",
                background: "var(--surface-2)", border: "1px solid var(--line)",
                color: "var(--text-primary)", font: "var(--type-body-sm)", cursor: "pointer",
              }}
            >
              Cross-Case Intel
            </button>
            <button
              type="button"
              onClick={() => navigate("/investigations")}
              style={{
                padding: "8px 16px", borderRadius: "var(--radius-input)",
                background: "var(--text-primary)", border: "none", color: "var(--canvas)",
                font: "var(--type-body-sm)", cursor: "pointer", fontWeight: 600,
              }}
            >
              + New Investigation
            </button>
          </div>
        </div>
      </Block>

      <Block className="block">
        <div className="t-label">Situation summary</div>
        <motion.div
          className={s.briefGrid}
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {situationStats.map(st => (
            <motion.div key={st.label} className={s.briefCard} variants={staggerItem}>
              <div className={s.briefNum}>{String(st.value).padStart(2, "0")}</div>
              <div className={s.briefLbl}>{st.label}</div>
            </motion.div>
          ))}
        </motion.div>
      </Block>

      <Block className={s.pSection}>
        <div className="t-label">Priority developments</div>
        {topPriorityCases.length === 0 ? (
          <div style={{
            padding: "var(--space-8) var(--space-6)", textAlign: "center",
            background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
            borderRadius: "var(--radius-card)", marginTop: "var(--space-3)",
          }}>
            <div style={{ font: "var(--type-mono-xs)", color: "var(--intel)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
              No priority developments
            </div>
            <p className="measure" style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", margin: "0 auto" }}>
              {backendOnline
                ? "No high or critical priority investigations are registered."
                : "Backend unavailable — no live intelligence is currently displayed."}
            </p>
          </div>
        ) : (
        <motion.ul
          className={s.pList}
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {topPriorityCases.map(b => (
            <motion.li
              key={b.id}
              className={s.pRow}
              variants={staggerItem}
              onClick={() => navigate(`/investigations/${b.id}/overview`)}
            >
              <div className={s.pMain}>
                <div className={s.pName}>
                  <span>{b.name}</span>
                  <span className={s.pId}>{b.id}</span>
                </div>
                <div className={s.pSummary}>{b.latest || b.brief}</div>
              </div>
              <div className={s.pMeta}>
                <PriorityMark priority={b.priority} />
                <span className={s.pUpdated}>{b.updated}</span>
              </div>
            </motion.li>
          ))}
        </motion.ul>
        )}
      </Block>

      <Block className={s.fSection}>
        <div className="t-label">Intelligence feed</div>
        {feed.length === 0 ? (
          <div style={{
            padding: "var(--space-8) var(--space-6)", textAlign: "center",
            background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
            borderRadius: "var(--radius-card)", marginTop: "var(--space-3)",
          }}>
            <p className="measure" style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", margin: "0 auto" }}>
              {backendOnline
                ? "No live case activity to report. Register an investigation to populate the feed."
                : "Backend unavailable — no live intelligence is currently displayed."}
            </p>
          </div>
        ) : (
        <motion.ul
          className={s.fList}
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          {feed.map(f => (
            <motion.li
              key={f.id}
              className={s.fRow}
              variants={staggerItem}
              onClick={() => navigate(f.to)}
            >
              <span className={s.fTime}>{f.time}</span>
              <span className={s.fText}>{f.text}</span>
            </motion.li>
          ))}
        </motion.ul>
        )}
      </Block>
    </div>
  );
}
