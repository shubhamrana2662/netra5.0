import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { Block } from "../../app/transitions";
import { useLiveStore } from "../../state/useLiveStore";
import { PriorityMark } from "../../components/primitives/PriorityMark";
import { Button } from "../../components/primitives/Button";
import { DemoBadge } from "../../components/DemoBadge";
import { captureRect } from "../../lib/flip";
import { EASE_OUT } from "../../lib/motion";
import type { CaseStatus, Priority } from "../../data/types";
import { cognitiveApi } from "../../api/cognitive";
import s from "./investigations.module.css";

const TABS: { id: CaseStatus | "ALL"; label: string }[] = [
  { id: "ALL", label: "All investigations" },
  { id: "ACTIVE", label: "Active" },
  { id: "ARCHIVED", label: "Archived" },
];

export function Investigations() {
  const navigate = useNavigate();
  const { cases, loading, backendOnline, empty, error, fetchCases, createCase } = useLiveStore();
  const [tab, setTab] = useState<CaseStatus | "ALL">("ALL");
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Form State
  const [title, setTitle] = useState("");
  const [firNumber, setFirNumber] = useState("");
  const [policeStation, setPoliceStation] = useState("Cyber Crime Police Station");
  const [priority, setPriority] = useState<Priority>("HIGH");
  const [description, setDescription] = useState("");
  const [crimeType, setCrimeType] = useState("UPI Fraud Syndicate");

  const [modalError, setModalError] = useState<string | null>(null);

  // Flight Simulator (Feature 11) State
  const [showSimModal, setShowSimModal] = useState(false);
  const [simTypology, setSimTypology] = useState("DIGITAL_ARREST");
  const [simSeed, setSimSeed] = useState(42);
  const [simGenerating, setSimGenerating] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);

  const handleGenerateBenchmark = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimGenerating(true);
    setSimError(null);
    try {
      const res = await cognitiveApi.generateBenchmark(simTypology, simSeed);
      await fetchCases();
      setShowSimModal(false);
      if (res && res.db_case_id) {
        navigate(`/investigations/${res.db_case_id}/overview`);
      } else if (res && res.case_id) {
        navigate(`/investigations/${res.case_id}/overview`);
      }
    } catch (err: unknown) {
      setSimError(err instanceof Error ? err.message : "Failed to generate benchmark case");
    } finally {
      setSimGenerating(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

  const [searchQuery, setSearchQuery] = useState("");

  const filtered = cases.filter(c => {
    if (tab !== "ALL" && c.status !== tab) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = (c.id || "").toLowerCase().includes(q);
      const matchName = (c.name || "").toLowerCase().includes(q);
      const matchDomain = (c.domain || "").toLowerCase().includes(q);
      const matchBrief = (c.brief || "").toLowerCase().includes(q);
      const matchNum = (((c as any).case_number as string) || "").toLowerCase().includes(q);
      return matchId || matchName || matchDomain || matchBrief || matchNum;
    }
    return true;
  });

  const openCase = (e: React.MouseEvent<HTMLLIElement>, id: string) => {
    const titleEl = e.currentTarget.querySelector<HTMLElement>(`.${s.caseName}`);
    captureRect(titleEl);
    navigate(`/investigations/${id}/overview`);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    setModalError(null);
    try {
      const created = await createCase({
        title: title.trim(),
        fir_number: firNumber.trim() || undefined,
        police_station: policeStation.trim() || undefined,
        priority: (priority === "CRITICAL" ? "high" : priority ? (priority.toLowerCase() as any) : "high"),
        description: description.trim() || undefined,
        crime_type: crimeType,
      });
      if (created) {
        setShowModal(false);
        setTitle("");
        setFirNumber("");
        setDescription("");
        navigate(`/investigations/${created.id}/overview`);
      } else {
        setModalError("Failed to register investigation. Please verify connection to the server.");
      }
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to register investigation.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <Block className={s.topRow}>
        <div>
          <h1 className={s.title}>Investigations</h1>
          <p className={s.lede}>
            {backendOnline
              ? "Live case repository with cryptographic audit custody."
              : "Backend unavailable — only the synthetic demonstration case is shown."}
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            onClick={() => setShowSimModal(true)}
            style={{
              background: "rgba(88, 166, 255, 0.10)",
              border: "1px solid rgba(88, 166, 255, 0.35)",
              color: "var(--accent)",
              padding: "9px 14px",
              borderRadius: "var(--radius-input)",
              font: "var(--type-mono-xs)",
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontWeight: 600,
            }}
          >
            ⚡ Flight Simulator · F11
          </button>
          <Button variant="primary" icon="plus" onClick={() => setShowModal(true)}>
            New investigation
          </Button>
        </div>
      </Block>

      <Block className={s.tabs}>
        {TABS.map(t => (
          <button
            key={t.id}
            className={`${s.tab} ${tab === t.id ? s.tabActive : ""}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
            {tab === t.id && (
              <motion.span
                layoutId="inv-tab"
                className={s.tabLine}
                transition={{ duration: 0.24, ease: EASE_OUT }}
              />
            )}
          </button>
        ))}
      </Block>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "var(--space-4)", marginBottom: "var(--space-2)", gap: "var(--space-4)", flexWrap: "wrap" }}>
        <div style={{ position: "relative", flex: 1, maxWidth: 420 }}>
          <input
            style={{
              width: "100%", height: 38, padding: "0 14px",
              background: "var(--surface-1)", border: "1px solid var(--line)",
              borderRadius: "var(--radius-input)", color: "var(--text-primary)",
              font: "var(--type-body-sm)", outline: "none",
            }}
            placeholder="Search by case ID, title, FIR number, or crime category…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="t-mono-xs" style={{ color: "var(--text-muted)" }}>
          Showing {filtered.length} of {cases.length} investigations
        </div>
      </div>

      <Block>
        {/* Scenario B — backend offline. No live intelligence is displayed. */}
        {!loading && !backendOnline && (
          <div role="alert" style={{
            padding: "var(--space-4) var(--space-5)", marginBottom: "var(--space-4)",
            background: "var(--critical-tint)", border: "1px solid rgba(255, 92, 92, 0.4)",
            borderRadius: "var(--radius-card)"
          }}>
            <div style={{ font: "var(--type-mono-xs)", letterSpacing: "0.08em", color: "var(--critical)", marginBottom: 6 }}>
              BACKEND UNAVAILABLE
            </div>
            <div style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", lineHeight: 1.6 }}>
              {error || "Unable to retrieve live investigation data."}<br />
              No live intelligence is currently displayed.
            </div>
          </div>
        )}

        {/* Scenario A — backend reachable but zero live investigations. */}
        {!loading && backendOnline && empty && (
          <div role="status" style={{
            padding: "var(--space-4) var(--space-5)", marginBottom: "var(--space-4)",
            background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
            borderRadius: "var(--radius-card)"
          }}>
            <div style={{ color: "var(--text-primary)", font: "var(--type-body)", marginBottom: 4 }}>
              No live investigations yet.
            </div>
            <div style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", lineHeight: 1.6 }}>
              Create an investigation or explore the clearly labelled synthetic demonstration case.
            </div>
          </div>
        )}

        {loading && cases.length === 0 ? (
          <div className={s.loadingState}>Connecting to live cases repository…</div>
        ) : filtered.length === 0 ? (
          <div style={{
            padding: "var(--space-12) var(--space-4)", textAlign: "center",
            background: "var(--surface-1)", border: "1px dashed var(--line)",
            borderRadius: "var(--radius-card)", marginTop: "var(--space-4)"
          }}>
            <div style={{ font: "var(--type-mono-xs)", color: "var(--intel)", marginBottom: 8, textTransform: "uppercase" }}>
              {searchQuery ? "Search Filter Results" : "No Investigations"}
            </div>
            <p style={{ color: "var(--text-secondary)", font: "var(--type-body)", marginBottom: "var(--space-4)" }}>
              {searchQuery
                ? `No investigations found matching "${searchQuery}".`
                : `No ${tab.toLowerCase()} investigations recorded in the system.`}
            </p>
            <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "center" }}>
              {searchQuery && (
                <Button variant="secondary" onClick={() => setSearchQuery("")}>
                  Clear Search
                </Button>
              )}
              <Button variant="primary" icon="plus" onClick={() => setShowModal(true)}>
                New Investigation
              </Button>
            </div>
          </div>
        ) : (
          <ul className={s.caseTable}>
            {filtered.map(c => (
              <li
                key={c.id}
                className={s.caseRow}
                onClick={e => openCase(e, c.id)}
              >
                <div className={s.caseMain}>
                  <div className={s.caseHead}>
                    <span className={s.caseId}>{c.id}</span>
                    <span className={s.caseName}>{c.name}</span>
                    {c.source_type === "SYNTHETIC_DEMO" && <DemoBadge size="sm" />}
                  </div>
                  <div className={s.caseDomain}>
                    {c.domain} · {c.brief ? c.brief.slice(0, 110) : "No description provided."}…
                  </div>
                  <div className={s.caseCounts}>
                    <span><b>{c.entities}</b> entities</span>
                    <span><b>{c.evidence}</b> evidence</span>
                    <span><b>{c.leads}</b> leads</span>
                  </div>
                </div>
                <div className={s.caseSide}>
                  <PriorityMark priority={c.priority} />
                  <span className={s.caseUpdated}>{c.updated}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Block>

      {/* Real Case Creation Modal */}
      <AnimatePresence>
        {showModal && (
          <div className={s.modalOverlay} onClick={() => setShowModal(false)}>
            <motion.div
              className={s.modalPanel}
              onClick={e => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 10 }}
            >
              <h2 className={s.modalTitle}>Register New Investigation</h2>
              <p className={s.modalSub}>
                Enters a verified case entry into PostgreSQL with cryptographic audit chain logging.
              </p>

              <form onSubmit={handleSubmit}>
                <div className={s.formGroup}>
                  <label className={s.formLabel}>Investigation Title / Operation Name *</label>
                  <input
                    className={s.formInput}
                    placeholder="e.g. Operation ShadowMule Phase II"
                    value={title}
                    onChange={e => setTitle(e.target.value)}
                    required
                    autoFocus
                  />
                </div>

                <div className={s.formRow}>
                  <div className={s.formGroup}>
                    <label className={s.formLabel}>FIR / Complaint Number</label>
                    <input
                      className={s.formInput}
                      placeholder="e.g. FIR-2026-9041"
                      value={firNumber}
                      onChange={e => setFirNumber(e.target.value)}
                    />
                  </div>
                  <div className={s.formGroup}>
                    <label className={s.formLabel}>Priority Level</label>
                    <select
                      className={s.formSelect}
                      value={priority || "HIGH"}
                      onChange={e => setPriority(e.target.value as Priority)}
                    >
                      <option value="CRITICAL">Critical (Immediate Intercept)</option>
                      <option value="HIGH">High (Active Syndicate)</option>
                      <option value="MEDIUM">Medium (Preliminary Inquiry)</option>
                    </select>
                  </div>
                </div>

                <div className={s.formRow}>
                  <div className={s.formGroup}>
                    <label className={s.formLabel}>Police Station / Cell</label>
                    <input
                      className={s.formInput}
                      value={policeStation}
                      onChange={e => setPoliceStation(e.target.value)}
                    />
                  </div>
                  <div className={s.formGroup}>
                    <label className={s.formLabel}>Crime Category</label>
                    <select
                      className={s.formSelect}
                      value={crimeType}
                      onChange={e => setCrimeType(e.target.value)}
                    >
                      <option value="UPI Fraud Syndicate">UPI Fraud Syndicate</option>
                      <option value="Digital Arrest Extortion">Digital Arrest Extortion</option>
                      <option value="Mule Account Network">Mule Account Network</option>
                      <option value="SIM Box / VoIP Rerouting">SIM Box / VoIP Rerouting</option>
                      <option value="Crypto Launder Escrow">Crypto Launder Escrow</option>
                    </select>
                  </div>
                </div>

                <div className={s.formGroup}>
                  <label className={s.formLabel}>Investigation Brief / Objective</label>
                  <textarea
                    className={s.formTextarea}
                    placeholder="Describe initial complaint, victim particulars, or financial loss..."
                    value={description}
                    onChange={e => setDescription(e.target.value)}
                  />
                </div>

                {modalError && (
                  <div style={{ color: "var(--critical)", font: "var(--type-mono-xs)", padding: "8px 12px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "var(--radius-input)", marginBottom: "var(--space-4)" }}>
                    {modalError}
                  </div>
                )}

                <div className={s.modalActions}>
                  <Button variant="secondary" type="button" onClick={() => setShowModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" type="submit" disabled={submitting}>
                    {submitting ? "Registering…" : "Create Investigation"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}

        {/* ── Feature 11: Flight Simulator Modal ──────────────────────── */}
        {showSimModal && (
          <div className={s.modalBackdrop} onClick={() => setShowSimModal(false)}>
            <motion.div
              className={s.modal}
              onClick={e => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.96, y: 10 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.96, y: 10 }}
              transition={{ duration: 0.2, ease: EASE_OUT }}
              style={{ maxWidth: 520 }}
            >
              <div className={s.modalHeader}>
                <div>
                  <div style={{ font: "var(--type-mono-xs)", color: "var(--accent)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "4px" }}>
                    Feature 11 · Adversarial Benchmark
                  </div>
                  <h2 className={s.modalTitle}>Synthetic Flight Simulator</h2>
                </div>
                <button className={s.closeBtn} onClick={() => setShowSimModal(false)}>✕</button>
              </div>

              <p style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-4)", lineHeight: 1.5 }}>
                Generates a DPDP-compliant synthetic test case with planted hidden links, adversarial OCR noise (8%), and dropped CDR records to benchmark analytical engines.
              </p>

              <form onSubmit={handleGenerateBenchmark}>
                <div className={s.formGroup}>
                  <label className={s.formLabel}>Crime Typology</label>
                  <select
                    className={s.formSelect}
                    value={simTypology}
                    onChange={e => setSimTypology(e.target.value)}
                  >
                    <option value="DIGITAL_ARREST">Digital Arrest Extortion (CBI / Police Spoof)</option>
                    <option value="TELEGRAM_INVESTMENT">Telegram Crypto Task / Investment Scam</option>
                    <option value="COURIER_SPOOF">Customs / Courier Narcotics Parcel Scam</option>
                    <option value="SIM_SWAP">SIM Swap & Unauthorized Banking Takeover</option>
                    <option value="MULE_LAYERING">Multi-Tier Mule Account Layering</option>
                  </select>
                </div>

                <div className={s.formGroup}>
                  <label className={s.formLabel}>Deterministic RNG Seed</label>
                  <input
                    type="number"
                    className={s.formInput}
                    value={simSeed}
                    onChange={e => setSimSeed(Number(e.target.value))}
                    min={1}
                    max={999999}
                  />
                  <span style={{ font: "var(--type-mono-xs)", color: "var(--text-tertiary)", marginTop: "4px", display: "block" }}>
                    Identical seeds yield 100% reproducible ground-truth graphs and planted links.
                  </span>
                </div>

                {simError && (
                  <div style={{ color: "var(--critical)", font: "var(--type-mono-xs)", padding: "8px 12px", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "var(--radius-input)", marginBottom: "var(--space-4)" }}>
                    {simError}
                  </div>
                )}

                <div className={s.modalActions}>
                  <Button variant="secondary" type="button" onClick={() => setShowSimModal(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" type="submit" disabled={simGenerating}>
                    {simGenerating ? "Synthesizing Case…" : "Launch Simulation"}
                  </Button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
