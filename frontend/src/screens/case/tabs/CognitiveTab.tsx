/**
 * CyberDrishti AI — Cognitive Forensic Intelligence Hub
 *
 * Master tab integrating all 11 cognitive engines into a single,
 * investigator-friendly interface with real-time data visualization.
 */
import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "../../../components/primitives/Button";
import { Icon } from "../../../components/icons";
import {
  cognitiveApi,
  type ContradictionsResponse,
  type HypothesesResponse,
  type NextBestActionsResponse,
  type MOFingerprintResponse,
  type CounterfactualResponse,
  type NetworkReplayResponse,
  type CrossCaseResponse,
  type VerifyDraftResponse,
  type BenchmarkCase,
} from "../../../api/cognitive";
import s from "./CognitiveTab.module.css";

/* ── Engine Registry ─────────────────────────────────────────────────── */

const ENGINES = [
  { id: "contradictions", label: "Contradictions", icon: "⚡", desc: "Ledger audit & impossible travel" },
  { id: "hypotheses", label: "Hypotheses", icon: "🎯", desc: "ACH suspect role classification" },
  { id: "nextbest", label: "Next-Best", icon: "🔮", desc: "Golden-Hours VoI urgency ranking" },
  { id: "mo", label: "MO Fingerprint", icon: "🔍", desc: "Crime script playbook matching" },
  { id: "counterfactual", label: "What-If", icon: "💰", desc: "Counterfactual freeze simulation" },
  { id: "replay", label: "Replay", icon: "🎬", desc: "CTDG temporal network frames" },
  { id: "crosscase", label: "Cross-Case", icon: "🔗", desc: "Zero-knowledge blind index" },
  { id: "verifier", label: "Verifier", icon: "🛡️", desc: "Output hallucination firewall" },
  { id: "benchmark", label: "Benchmark", icon: "🧪", desc: "Synthetic test case generator" },
] as const;

type EngineId = (typeof ENGINES)[number]["id"];

/* ── Component ───────────────────────────────────────────────────────── */

export function CognitiveTab({ caseId }: { caseId: string }) {
  const [activeEngine, setActiveEngine] = useState<EngineId>("contradictions");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Engine-specific data
  const [contradictions, setContradictions] = useState<ContradictionsResponse | null>(null);
  const [hypotheses, setHypotheses] = useState<HypothesesResponse | null>(null);
  const [nextBest, setNextBest] = useState<NextBestActionsResponse | null>(null);
  const [moResult, setMoResult] = useState<MOFingerprintResponse | null>(null);
  const [cfResult, setCfResult] = useState<CounterfactualResponse | null>(null);
  const [replayResult, setReplayResult] = useState<NetworkReplayResponse | null>(null);
  const [crossCase, setCrossCase] = useState<CrossCaseResponse | null>(null);
  const [verifyResult, setVerifyResult] = useState<VerifyDraftResponse | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkCase | null>(null);

  // Input state for interactive engines
  const [freezeAccount, setFreezeAccount] = useState("");
  const [freezeTime, setFreezeTime] = useState("");
  const [verifyText, setVerifyText] = useState("");
  const [benchTypology, setBenchTypology] = useState("DIGITAL_ARREST");

  const runEngine = useCallback(async (engineId: EngineId) => {
    setLoading(true);
    setError(null);
    try {
      switch (engineId) {
        case "contradictions": {
          const r = await cognitiveApi.contradictions(caseId);
          setContradictions(r);
          break;
        }
        case "hypotheses": {
          const r = await cognitiveApi.hypotheses(caseId);
          setHypotheses(r);
          break;
        }
        case "nextbest": {
          const r = await cognitiveApi.nextBestActions(caseId);
          setNextBest(r);
          break;
        }
        case "mo": {
          const r = await cognitiveApi.moFingerprint(caseId);
          setMoResult(r);
          break;
        }
        case "replay": {
          const r = await cognitiveApi.networkReplay(caseId);
          setReplayResult(r);
          break;
        }
        case "crosscase": {
          const r = await cognitiveApi.crossCaseCollisions();
          setCrossCase(r);
          break;
        }
      }
    } catch (err: unknown) {
      setError((err as Error)?.message || "Engine execution failed.");
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  // Auto-run when engine changes (for non-interactive engines)
  useEffect(() => {
    const autoRun: EngineId[] = ["contradictions", "hypotheses", "nextbest", "mo", "replay", "crosscase"];
    if (autoRun.includes(activeEngine)) {
      runEngine(activeEngine);
    }
  }, [activeEngine, caseId, runEngine]);

  const handleCounterfactual = async () => {
    if (!freezeAccount.trim() || !freezeTime.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const r = await cognitiveApi.counterfactualFreeze(caseId, freezeAccount, freezeTime);
      setCfResult(r);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Counterfactual simulation failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async () => {
    if (!verifyText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const r = await cognitiveApi.verifyDraft(verifyText, caseId);
      setVerifyResult(r);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Verification failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleBenchmark = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await cognitiveApi.generateBenchmark(benchTypology);
      setBenchmark(r);
    } catch (err: unknown) {
      setError((err as Error)?.message || "Benchmark generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const currentEngine = ENGINES.find(e => e.id === activeEngine)!;

  return (
    <div className={s.cogRoot}>
      {/* Engine Selector Ribbon */}
      <nav className={s.selectorRibbon} aria-label="Cognitive engines">
        {ENGINES.map(eng => (
          <button
            key={eng.id}
            className={activeEngine === eng.id ? s.engineChipActive : s.engineChip}
            onClick={() => setActiveEngine(eng.id)}
            title={eng.desc}
          >
            <span>{eng.icon}</span>
            <span>{eng.label}</span>
          </button>
        ))}
      </nav>

      {/* Panel */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeEngine}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
          className={s.panel}
        >
          <div className={s.panelHeader}>
            <div className={s.panelHeaderLeft}>
              <span className={s.engineBadge}>
                <span>{currentEngine.icon}</span>
                F{String(ENGINES.indexOf(currentEngine) + 2).padStart(2, "0")}
              </span>
              <div>
                <h3 className={s.panelTitle}>{currentEngine.label}</h3>
                <p className={s.panelSubtitle}>{currentEngine.desc}</p>
              </div>
            </div>
            {["contradictions", "hypotheses", "nextbest", "mo", "replay", "crosscase"].includes(activeEngine) && (
              <Button variant="secondary" onClick={() => runEngine(activeEngine)} disabled={loading}>
                {loading ? "Running…" : "Refresh"}
              </Button>
            )}
          </div>

          <div className={s.panelBody}>
            {error && (
              <div style={{ padding: "var(--space-4)", background: "var(--critical-tint)", border: "1px solid rgba(255,92,92,0.3)", borderRadius: "var(--radius-input)", marginBottom: "var(--space-4)", color: "var(--critical)", font: "var(--type-body-sm)" }}>
                {error}
              </div>
            )}

            {loading ? (
              <div className={s.loading}>
                <div className={s.spinner} />
                <span style={{ font: "var(--type-mono-xs)", color: "var(--text-muted)" }}>
                  Running {currentEngine.label} engine…
                </span>
              </div>
            ) : (
              <>
                {/* ── Contradictions Panel ─────────────────────────── */}
                {activeEngine === "contradictions" && (
                  contradictions ? (
                    <div>
                      <div className={s.cardGrid}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Ledger Rows Audited</div>
                          <div className={s.cardValue}>{contradictions.ledger_audit.input_rows}</div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Balance Breaks</div>
                          <div className={s.cardValue} style={{ color: contradictions.ledger_audit.findings.length > 0 ? "var(--critical)" : "var(--verified)" }}>
                            {contradictions.ledger_audit.findings.length}
                          </div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Impossible Travel</div>
                          <div className={s.cardValue} style={{ color: contradictions.impossible_travel.findings.length > 0 ? "var(--warning)" : "var(--verified)" }}>
                            {contradictions.impossible_travel.findings.length}
                          </div>
                        </div>
                      </div>

                      {contradictions.ledger_audit.findings.length > 0 && (
                        <div style={{ marginTop: "var(--space-6)" }}>
                          <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Ledger Anomalies</div>
                          {contradictions.ledger_audit.findings.map((f, i) => (
                            <div key={i} className={s.findingRow}>
                              <div className={s.findingSeverityCritical} />
                              <div className={s.findingBody}>
                                <div className={s.findingKind} style={{ color: "var(--critical)" }}>{f.kind}</div>
                                <div className={s.findingText}>{f.explanation}</div>
                                <div className={s.findingMeta}>
                                  Row {f.row_index} · Expected ₹{f.expected_balance?.toLocaleString()} · Reported ₹{f.reported_balance?.toLocaleString()} · Gap ₹{f.discrepancy?.toLocaleString()}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {contradictions.impossible_travel.findings.length > 0 && (
                        <div style={{ marginTop: "var(--space-6)" }}>
                          <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Impossible Travel Detections</div>
                          {contradictions.impossible_travel.findings.map((f, i) => (
                            <div key={i} className={s.findingRow}>
                              <div className={s.findingSeverityWarning} />
                              <div className={s.findingBody}>
                                <div className={s.findingKind} style={{ color: "var(--warning)" }}>{f.kind}</div>
                                <div className={s.findingText}>{f.explanation}</div>
                                <div className={s.findingMeta}>
                                  {f.entity} · {f.distance_km?.toFixed(1)}km in {f.time_gap_s}s ({f.velocity_kmh?.toFixed(0)} km/h)
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {contradictions.ledger_audit.findings.length === 0 && contradictions.impossible_travel.findings.length === 0 && (
                        <div className={s.emptyState} style={{ marginTop: "var(--space-6)" }}>
                          <div className={s.emptyIcon}>✅</div>
                          <div style={{ font: "var(--type-body)", color: "var(--verified)" }}>No contradictions detected</div>
                          <div style={{ font: "var(--type-body-sm)" }}>All ledger rows pass continuity checks. No impossible travel detected.</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>⚡</div>
                      <div>No contradiction data available</div>
                      <div style={{ font: "var(--type-body-sm)" }}>Upload bank statements and CDRs to enable ledger audit and travel checks.</div>
                    </div>
                  )
                )}

                {/* ── Hypotheses Panel ────────────────────────────── */}
                {activeEngine === "hypotheses" && (
                  hypotheses ? (
                    <div>
                      <div className={s.cardGrid} style={{ marginBottom: "var(--space-6)" }}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Assessment</div>
                          <div className={s.cardValue} style={{ fontSize: "1.2em" }}>{hypotheses.display_label}</div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Type</div>
                          <div className={s.cardValue} style={{ fontSize: "1em" }}>{hypotheses.assessment_type}</div>
                        </div>
                      </div>

                      <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Posterior Probabilities</div>
                      {hypotheses.hypotheses.map((h, i) => {
                        const pct = Math.round(h.posterior * 100);
                        const color = h.classification === "SUSPECT" ? "var(--critical)" :
                                     h.classification === "MULE" ? "var(--warning)" :
                                     h.classification === "VICTIM" ? "var(--verified)" : "var(--accent)";
                        return (
                          <div key={i} className={s.hypothesisBar}>
                            <span className={s.hypLabel}>{h.label}</span>
                            <div className={s.hypBarTrack}>
                              <div className={s.hypBarFill} style={{ width: `${pct}%`, background: color }} />
                            </div>
                            <span className={s.hypScore}>{pct}%</span>
                          </div>
                        );
                      })}

                      {hypotheses.unobserved_indicators && hypotheses.unobserved_indicators.length > 0 && (
                        <div style={{ marginTop: "var(--space-6)" }}>
                          <div className="t-label" style={{ marginBottom: "var(--space-2)" }}>Unobserved Indicators</div>
                          <p style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)" }}>
                            These indicators could refine the classification if observed:
                          </p>
                          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)", marginTop: "var(--space-2)" }}>
                            {hypotheses.unobserved_indicators.map((ind, i) => (
                              <span key={i} className={s.metaCategory}>{ind}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>🎯</div>
                      <div>No hypothesis data available</div>
                      <div style={{ font: "var(--type-body-sm)" }}>Upload evidence to enable ACH suspect role classification.</div>
                    </div>
                  )
                )}

                {/* ── Next-Best Actions Panel ─────────────────────── */}
                {activeEngine === "nextbest" && (
                  nextBest ? (
                    <div>
                      <div className={s.cardGrid} style={{ marginBottom: "var(--space-6)" }}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Elapsed Hours</div>
                          <div className={s.cardValue}>{nextBest.elapsed_hours}h</div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Golden Window</div>
                          <div className={s.cardValue} style={{ color: nextBest.elapsed_hours <= nextBest.golden_hours ? "var(--verified)" : "var(--critical)" }}>
                            {nextBest.golden_hours}h
                          </div>
                          <div className={s.cardMeta}>
                            {nextBest.elapsed_hours <= nextBest.golden_hours ? "⏰ Within golden hours" : "⚠️ Past golden window"}
                          </div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Top Urgency</div>
                          <div className={s.cardValue}>{nextBest.urgency_factor?.toFixed(2)}</div>
                        </div>
                      </div>

                      <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Ranked Investigation Actions</div>
                      {nextBest.ranked_actions.map((a, i) => (
                        <div key={i} className={s.actionCard}>
                          <div className={s.actionRank}>{i + 1}</div>
                          <div className={s.actionBody}>
                            <div className={s.actionTitle}>{a.action}</div>
                            <div className={s.actionInstructions}>{a.instructions}</div>
                            <div className={s.actionMeta}>
                              <span className={s.metaUrgent}>Score: {a.urgency_score?.toFixed(2)}</span>
                              <span className={s.metaCategory}>{a.category}</span>
                              {a.time_window && <span className={s.metaWindow}>{a.time_window}</span>}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>🔮</div>
                      <div>No next-best action data available</div>
                    </div>
                  )
                )}

                {/* ── MO Fingerprint Panel ────────────────────────── */}
                {activeEngine === "mo" && (
                  moResult ? (
                    <div>
                      <div className={s.cardGrid} style={{ marginBottom: "var(--space-6)" }}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Verdict</div>
                          <div className={s.cardValue} style={{
                            color: moResult.verdict === "MATCHED" ? "var(--verified)" :
                                   moResult.verdict === "NO_CONFIDENT_MATCH" ? "var(--warning)" : "var(--text-muted)"
                          }}>
                            {moResult.verdict}
                          </div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Observed Stages</div>
                          <div className={s.cardValue}>{moResult.observed_sequence?.length || 0}</div>
                        </div>
                      </div>

                      {moResult.best_match && (
                        <div style={{ marginBottom: "var(--space-6)", padding: "var(--space-5)", background: "rgba(80, 200, 120, 0.04)", border: "1px solid rgba(80, 200, 120, 0.2)", borderRadius: "var(--radius-input)" }}>
                          <div style={{ font: "var(--type-mono-xs)", color: "var(--verified)", letterSpacing: "0.06em", marginBottom: "var(--space-2)" }}>BEST MATCH</div>
                          <div style={{ font: "var(--type-body)", fontWeight: 600, color: "var(--text-primary)" }}>{moResult.best_match.playbook}</div>
                          <div style={{ font: "var(--type-body-sm)", color: "var(--text-secondary)", marginTop: 4 }}>
                            Similarity: {(moResult.best_match.similarity * 100).toFixed(1)}% · Source: {moResult.best_match.source}
                          </div>
                        </div>
                      )}

                      <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Playbook Matches</div>
                      {moResult.matches?.map((m, i) => (
                        <div key={i} className={s.moMatch}>
                          <div className={s.moName}>{m.playbook}</div>
                          <div className={s.moSimilarityBar}>
                            <div className={s.moBarTrack}>
                              <div className={s.moBarFill} style={{ width: `${m.similarity * 100}%` }} />
                            </div>
                            <span className={s.moScore}>{(m.similarity * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                      ))}

                      {moResult.note && (
                        <p style={{ font: "var(--type-mono-xs)", color: "var(--text-muted)", marginTop: "var(--space-4)", fontStyle: "italic" }}>
                          {moResult.note}
                        </p>
                      )}
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>🔍</div>
                      <div>No MO fingerprint data</div>
                      <div style={{ font: "var(--type-body-sm)" }}>Upload WhatsApp/SMS transcripts for crime script analysis.</div>
                    </div>
                  )
                )}

                {/* ── Counterfactual What-If Panel ────────────────── */}
                {activeEngine === "counterfactual" && (
                  <div>
                    <div className={s.inputRow}>
                      <input
                        className={s.inputField}
                        placeholder="Account to freeze (e.g. user@upi)"
                        value={freezeAccount}
                        onChange={e => setFreezeAccount(e.target.value)}
                      />
                      <input
                        className={s.inputField}
                        placeholder="Freeze time (ISO-8601)"
                        value={freezeTime}
                        onChange={e => setFreezeTime(e.target.value)}
                        style={{ maxWidth: 260 }}
                      />
                      <Button variant="primary" onClick={handleCounterfactual} disabled={loading}>
                        Simulate Freeze
                      </Button>
                    </div>

                    {cfResult && (
                      <div>
                        <div className={s.cfSummary}>
                          <div className={s.cfMetric}>
                            <div className={s.cfMetricValue}>₹{cfResult.preserved_total?.toLocaleString()}</div>
                            <div className={s.cfMetricLabel}>Preserved Capital</div>
                          </div>
                          <div className={s.cfMetric}>
                            <div className={s.cfMetricValue} style={{ color: "var(--critical)" }}>{cfResult.blocked_debits}</div>
                            <div className={s.cfMetricLabel}>Blocked Debits</div>
                          </div>
                          <div className={s.cfMetric}>
                            <div className={s.cfMetricValue} style={{ color: "var(--warning)" }}>{cfResult.stopped_credits}</div>
                            <div className={s.cfMetricLabel}>Stopped Credits</div>
                          </div>
                          <div className={s.cfMetric}>
                            <div className={s.cfMetricValue} style={{ color: "var(--accent)" }}>{cfResult.completed_transfers}</div>
                            <div className={s.cfMetricLabel}>Completed</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* ── Network Replay Panel ────────────────────────── */}
                {activeEngine === "replay" && (
                  replayResult ? (
                    <div>
                      <div className={s.cardGrid} style={{ marginBottom: "var(--space-6)" }}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Total Events</div>
                          <div className={s.cardValue}>{replayResult.total_events}</div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Animation Frames</div>
                          <div className={s.cardValue}>{replayResult.total_frames}</div>
                        </div>
                      </div>

                      {replayResult.frames.length > 0 ? (
                        <div>
                          <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Frame Timeline</div>
                          {replayResult.frames.slice(0, 20).map((f, i) => (
                            <div key={i} className={s.findingRow}>
                              <div className={s.findingSeverityInfo} />
                              <div className={s.findingBody}>
                                <div className={s.findingKind} style={{ color: "var(--intel)" }}>Frame {i + 1}</div>
                                <div className={s.findingText}>
                                  {f.nodes?.length || 0} nodes · {f.edges?.length || 0} edges
                                </div>
                                <div className={s.findingMeta}>
                                  {f.t_start} → {f.t_end}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className={s.emptyState}>
                          <div className={s.emptyIcon}>🎬</div>
                          <div>No replay frames generated</div>
                          <div style={{ font: "var(--type-body-sm)" }}>Not enough timestamped events for temporal network reconstruction.</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>🎬</div>
                      <div>No replay data available</div>
                    </div>
                  )
                )}

                {/* ── Cross-Case Collisions Panel ─────────────────── */}
                {activeEngine === "crosscase" && (
                  crossCase ? (
                    <div>
                      <div className={s.cardGrid} style={{ marginBottom: "var(--space-6)" }}>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Entities Indexed</div>
                          <div className={s.cardValue}>{crossCase.total_entities_indexed}</div>
                        </div>
                        <div className={s.dataCard}>
                          <div className={s.cardLabel}>Collisions Found</div>
                          <div className={s.cardValue} style={{ color: crossCase.total_collisions > 0 ? "var(--warning)" : "var(--verified)" }}>
                            {crossCase.total_collisions}
                          </div>
                        </div>
                      </div>

                      {crossCase.collisions.length > 0 ? (
                        <div>
                          <div className="t-label" style={{ marginBottom: "var(--space-3)" }}>Entity Collisions (Zero-Knowledge)</div>
                          {crossCase.collisions.map((c, i) => (
                            <div key={i} className={s.collisionRow}>
                              <span className={s.metaCategory}>{c.entity_type}</span>
                              <span className={s.collisionToken}>{c.blind_token?.slice(0, 16)}…</span>
                              <div className={s.collisionCases}>
                                {c.cases?.map((caseRef, j) => (
                                  <span key={j} className={s.caseTag}>{caseRef}</span>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className={s.emptyState} style={{ marginTop: "var(--space-4)" }}>
                          <div className={s.emptyIcon}>✅</div>
                          <div>No cross-case collisions detected</div>
                        </div>
                      )}

                      <p style={{ font: "var(--type-mono-xs)", color: "var(--text-muted)", marginTop: "var(--space-4)", fontStyle: "italic" }}>
                        {crossCase.note}
                      </p>
                    </div>
                  ) : (
                    <div className={s.emptyState}>
                      <div className={s.emptyIcon}>🔗</div>
                      <div>No cross-case data available</div>
                    </div>
                  )
                )}

                {/* ── Verifier Panel ──────────────────────────────── */}
                {activeEngine === "verifier" && (
                  <div>
                    <p className="t-body-sm" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
                      Paste any draft text (report, copilot output, etc.) to run deterministic statutory and factual validation.
                    </p>
                    <textarea
                      className={s.inputField}
                      style={{ minHeight: 120, resize: "vertical", padding: "var(--space-4)", width: "100%", boxSizing: "border-box" }}
                      placeholder="Paste text to verify…"
                      value={verifyText}
                      onChange={e => setVerifyText(e.target.value)}
                    />
                    <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "var(--space-3)" }}>
                      <Button variant="primary" onClick={handleVerify} disabled={loading || !verifyText.trim()}>
                        Run Verifier
                      </Button>
                    </div>

                    {verifyResult && (
                      <div className={verifyResult.passed ? s.verifierPassed : s.verifierFailed}>
                        <div className={verifyResult.passed ? s.verifierPassedTitle : s.verifierFailedTitle}>
                          <span>{verifyResult.passed ? "✅" : "⚠️"}</span>
                          {verifyResult.passed ? "All checks passed" : `${verifyResult.flags?.length || 0} issue(s) detected`}
                        </div>
                        {verifyResult.flags?.map((f, i) => (
                          <div key={i} className={s.flagRow}>
                            <span className={
                              f.severity === "error" ? s.flagError :
                              f.severity === "warning" ? s.flagWarn : s.flagInfo
                            }>
                              {f.severity}
                            </span>
                            <span className={s.flagMessage}>{f.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* ── Benchmark Panel ─────────────────────────────── */}
                {activeEngine === "benchmark" && (
                  <div>
                    <p className="t-body-sm" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
                      Generate a DPDP-compliant synthetic test case with hidden links, noise entities, and ground truth for system validation.
                    </p>
                    <div className={s.inputRow}>
                      <select
                        className={s.inputField}
                        value={benchTypology}
                        onChange={e => setBenchTypology(e.target.value)}
                        style={{ maxWidth: 300 }}
                      >
                        <option value="DIGITAL_ARREST">Digital Arrest</option>
                        <option value="CRYPTO_PIG_BUTCHERING">Crypto Pig Butchering</option>
                        <option value="LOAN_APP_HARASSMENT">Loan App Harassment</option>
                        <option value="TASK_FRAUD">Task Fraud</option>
                        <option value="KYC_PHISHING">KYC Phishing</option>
                      </select>
                      <Button variant="primary" onClick={handleBenchmark} disabled={loading}>
                        Generate Case
                      </Button>
                    </div>

                    {benchmark && (
                      <div>
                        <div className={s.cardGrid}>
                          <div className={s.dataCard}>
                            <div className={s.cardLabel}>Case ID</div>
                            <div className={s.cardValue} style={{ fontSize: "0.85em" }}>{benchmark.case_id}</div>
                          </div>
                          <div className={s.dataCard}>
                            <div className={s.cardLabel}>Typology</div>
                            <div className={s.cardValue} style={{ fontSize: "0.85em" }}>{benchmark.typology}</div>
                          </div>
                          <div className={s.dataCard}>
                            <div className={s.cardLabel}>Entities</div>
                            <div className={s.cardValue}>{benchmark.entities_count}</div>
                          </div>
                          <div className={s.dataCard}>
                            <div className={s.cardLabel}>Flow Edges</div>
                            <div className={s.cardValue}>{benchmark.flow_edges_count}</div>
                          </div>
                          <div className={s.dataCard}>
                            <div className={s.cardLabel}>Hidden Links</div>
                            <div className={s.cardValue} style={{ color: "var(--warning)" }}>{benchmark.hidden_links_count}</div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
