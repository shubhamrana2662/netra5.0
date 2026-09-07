import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Block } from "../../app/transitions";
import { intelApi, type CrossMatchResponse, type SyndicateEntity } from "../../api/intelligence";
import { Button } from "../../components/primitives/Button";
import { Icon } from "../../components/icons";
import { PriorityMark } from "../../components/primitives/PriorityMark";
import s from "./intelligence.module.css";

export function Intelligence() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [crossResult, setCrossResult] = useState<CrossMatchResponse | null>(null);
  const [syndicates, setSyndicates] = useState<SyndicateEntity[]>([]);
  const [loadingSyndicates, setLoadingSyndicates] = useState(false);
  const [searchErr, setSearchErr] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"SEARCH" | "SYNDICATES" | "FINDINGS">("SEARCH");

  useEffect(() => {
    // Load top cross-case syndicates and initial cross-match on mount
    const loadInitialIntel = async () => {
      setLoadingSyndicates(true);
      try {
        const [synRes, initialMatch] = await Promise.allSettled([
          intelApi.syndicates(30),
          intelApi.crossMatch(),
        ]);
        if (synRes.status === "fulfilled") {
          setSyndicates(synRes.value.syndicates || []);
        }
        if (initialMatch.status === "fulfilled") {
          setCrossResult(initialMatch.value);
        }
      } catch (err) {
        console.warn("Error loading cross-case intelligence:", err);
      } finally {
        setLoadingSyndicates(false);
      }
    };
    loadInitialIntel();
  }, []);

  const runSearch = async (searchTerm: string) => {
    const term = searchTerm.trim();
    if (!term) return;
    setQuery(term);
    setSearching(true);
    setSearchErr(null);
    setViewMode("SEARCH");

    try {
      const res = await intelApi.crossMatch(term);
      setCrossResult(res);
    } catch (err: unknown) {
      setSearchErr("Cross-match search failed. Please verify backend connection.");
    } finally {
      setSearching(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(query);
  };

  // Quick-lookup suggestions are derived from real detected syndicates only.
  // No hardcoded IOCs or fabricated "N cases" counts.
  const recommendationPills = syndicates.slice(0, 6).map(syn => ({
    label: syn.canonical_value,
    desc: `${syn.case_count} case${syn.case_count === 1 ? "" : "s"}`,
  }));

  return (
    <div className="page">
      <Block>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div>
            <h1 className={s.title}>Cross-Case Threat Intelligence</h1>
            <p className={s.lede}>
              Syndicate detection, cross-investigation entity matching, and topological IOC linkage.
            </p>
          </div>

          <div style={{ display: "flex", gap: "var(--space-2)", background: "var(--surface-1)", padding: "4px", borderRadius: "var(--radius-input)", border: "1px solid var(--line)" }}>
            <button
              onClick={() => setViewMode("SEARCH")}
              style={{
                padding: "6px 14px", borderRadius: "var(--radius-input)", border: "none",
                background: viewMode === "SEARCH" ? "var(--surface-3)" : "transparent",
                color: viewMode === "SEARCH" ? "var(--text-primary)" : "var(--text-muted)",
                font: "var(--type-mono-xs)", cursor: "pointer",
              }}
            >
              IOC SEARCH ({crossResult?.total_matches || 0})
            </button>
            <button
              onClick={() => setViewMode("SYNDICATES")}
              style={{
                padding: "6px 14px", borderRadius: "var(--radius-input)", border: "none",
                background: viewMode === "SYNDICATES" ? "var(--surface-3)" : "transparent",
                color: viewMode === "SYNDICATES" ? "var(--text-primary)" : "var(--text-muted)",
                font: "var(--type-mono-xs)", cursor: "pointer",
              }}
            >
              MULTI-CASE SYNDICATES ({syndicates.length})
            </button>
            <button
              onClick={() => setViewMode("FINDINGS")}
              style={{
                padding: "6px 14px", borderRadius: "var(--radius-input)", border: "none",
                background: viewMode === "FINDINGS" ? "var(--surface-3)" : "transparent",
                color: viewMode === "FINDINGS" ? "var(--text-primary)" : "var(--text-muted)",
                font: "var(--type-mono-xs)", cursor: "pointer",
              }}
            >
              ANALYTICAL FINDINGS ({crossResult?.total_matches || 0})
            </button>
          </div>
        </div>
      </Block>

      {/* Cross-Match IOC Lookup Panel */}
      <Block>
        <div style={{ padding: "var(--space-6)", background: "var(--surface-1)", border: "1px solid var(--line)", borderRadius: "var(--radius-card)", marginBottom: "var(--space-8)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "var(--space-2)" }}>
            <Icon name="search" size={16} />
            <span className="t-label">Cross-Case IOC & Entity Matcher</span>
          </div>
          <p className="t-body-sm measure" style={{ color: "var(--text-secondary)", marginBottom: "var(--space-4)" }}>
            Query suspect mobile numbers, mule bank accounts, burner phones, or UPI VPA addresses across all registered investigations.
          </p>

          <form onSubmit={handleSearchSubmit} style={{ display: "flex", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
            <input
              style={{
                flex: 1, height: 42, padding: "0 var(--space-4)",
                background: "var(--surface-2)", border: "1px solid var(--line)",
                borderRadius: "var(--radius-input)", color: "var(--text-primary)",
                font: "var(--type-body-sm)", outline: "none",
              }}
              placeholder="Search phone number, UPI handle, bank account, IP, or email across all matters..."
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
            <Button variant="primary" type="submit" disabled={searching}>
              {searching ? "Searching…" : "Cross Match"}
            </Button>
          </form>

          {/* Quick-Match Suggestion Pills — real detected syndicates only */}
          {recommendationPills.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <span className="t-mono-xs" style={{ color: "var(--text-muted)" }}>Quick Lookups:</span>
            {recommendationPills.map(p => (
              <button
                key={p.label}
                type="button"
                onClick={() => runSearch(p.label)}
                style={{
                  background: "var(--surface-2)", border: "1px solid var(--line)",
                  borderRadius: "12px", padding: "3px 10px", color: "var(--text-secondary)",
                  font: "var(--type-mono-xs)", cursor: "pointer", display: "flex", gap: "6px",
                  alignItems: "center",
                }}
              >
                <span>{p.label}</span>
                <span style={{ color: "var(--intel)", fontSize: "10px" }}>({p.desc})</span>
              </button>
            ))}
          </div>
          )}

          {searchErr && (
            <div style={{ marginTop: "var(--space-3)", color: "var(--critical)", font: "var(--type-mono-xs)" }}>
              {searchErr}
            </div>
          )}
        </div>
      </Block>

      {/* Main Tab Content */}
      {viewMode === "SEARCH" && (
        <Block>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
            <div className="t-label">
              {crossResult ? `Cross-Case Match Results for "${crossResult.query}"` : "Active Cross-Case Matches"}
            </div>
            {crossResult && (
              <span className="t-mono-xs" style={{ color: "var(--intel)" }}>
                {crossResult.total_matches} MATCH(ES) DETECTED
              </span>
            )}
          </div>

          {crossResult && crossResult.matches.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {crossResult.matches.map((m, idx) => (
                <div
                  key={`${m.case_id}-${idx}`}
                  onClick={() => navigate(`/investigations/${m.case_id}/overview`)}
                  style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "14px 18px", background: "var(--surface-1)",
                    border: "1px solid var(--line)", borderRadius: "var(--radius-card)",
                    cursor: "pointer", transition: "border-color var(--dur-2)",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = "var(--line-strong)")}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--line)")}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span style={{ font: "600 15px var(--font-sans)", color: "var(--text-primary)" }}>
                        {m.case_title}
                      </span>
                      <span className="t-mono-xs" style={{ padding: "2px 6px", background: "var(--surface-3)", borderRadius: "4px", color: "var(--text-muted)" }}>
                        {m.case_number}
                      </span>
                      {m.crime_type && (
                        <span className="t-mono-xs" style={{ color: "var(--text-secondary)" }}>
                          · {m.crime_type}
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", font: "var(--type-mono-xs)" }}>
                      <span style={{ color: "var(--intel)", fontWeight: 600 }}>
                        {m.entity_type}:
                      </span>
                      <span style={{ color: "var(--text-primary)" }}>
                        {m.entity_value}
                      </span>
                      <span style={{ color: "var(--text-muted)" }}>
                        · {m.mention_count} mention(s) in evidence
                      </span>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
                    <PriorityMark priority={(m.priority?.toUpperCase() as any) || "HIGH"} />
                    <Button variant="ghost" icon="arrow" onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/investigations/${m.case_id}/overview`);
                    }}>
                      Investigate
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ padding: "var(--space-8)", textAlign: "center", background: "var(--surface-1)", border: "1px solid var(--line)", borderRadius: "var(--radius-card)", color: "var(--text-muted)" }}>
              No matches found. Try searching a phone number, UPI handle, or choose one of the quick lookups above.
            </div>
          )}
        </Block>
      )}

      {viewMode === "SYNDICATES" && (
        <Block>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-4)" }}>
            <div>
              <div className="t-label">Identified Multi-Case Syndicates ({syndicates.length})</div>
              <p className="t-body-sm" style={{ color: "var(--text-secondary)" }}>
                Entities appearing across multiple distinct investigations, indicating coordinated cybercrime operations.
              </p>
            </div>
          </div>

          {loadingSyndicates ? (
            <div style={{ padding: "var(--space-8)", textAlign: "center", color: "var(--text-muted)" }}>
              Analyzing national cross-case graph…
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {syndicates.map((syn, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: "16px 20px", background: "var(--surface-1)",
                    border: "1px solid var(--line)", borderRadius: "var(--radius-card)",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--space-3)", flexWrap: "wrap", gap: "var(--space-2)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span className="t-mono-xs" style={{
                        padding: "3px 8px", background: "rgba(59, 130, 246, 0.15)",
                        border: "1px solid rgba(59, 130, 246, 0.3)", borderRadius: "4px",
                        color: "var(--intel)", fontWeight: 600,
                      }}>
                        {syn.entity_type}
                      </span>
                      <span style={{ font: "600 16px var(--font-sans)", color: "var(--text-primary)" }}>
                        {syn.canonical_value}
                      </span>
                      <span className="t-mono-xs" style={{
                        padding: "2px 8px", background: "rgba(239, 68, 68, 0.15)",
                        color: "var(--critical)", borderRadius: "10px", fontWeight: 600,
                      }}>
                        Linked across {syn.case_count} cases
                      </span>
                    </div>

                    <Button variant="secondary" onClick={() => runSearch(syn.canonical_value)}>
                      Cross-Match IOC
                    </Button>
                  </div>

                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {syn.cases.map(c => (
                      <button
                        key={c.case_id}
                        onClick={() => navigate(`/investigations/${c.case_id}/overview`)}
                        style={{
                          background: "var(--surface-2)", border: "1px solid var(--line)",
                          borderRadius: "var(--radius-input)", padding: "4px 10px",
                          font: "var(--type-mono-xs)", color: "var(--text-secondary)",
                          cursor: "pointer", display: "flex", gap: "6px", alignItems: "center",
                        }}
                      >
                        <span style={{ color: "var(--text-primary)", fontWeight: 500 }}>{c.case_number}</span>
                        <span>·</span>
                        <span>{c.case_title.length > 25 ? `${c.case_title.slice(0, 22)}…` : c.case_title}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Block>
      )}

      {viewMode === "FINDINGS" && (
        <Block>
          <div className="t-label" style={{ marginBottom: "var(--space-4)" }}>
            Cross-Case Analytical Findings ({crossResult?.total_matches || 0})
          </div>
          {crossResult && crossResult.matches.length > 0 ? (
            <ul className={s.fndList}>
              {crossResult.matches.map((m, idx) => (
                <li key={`${m.case_id}-${idx}`} className={s.fndCard}>
                  <div className={s.fndHead}>
                    <span className={s.fndScope}>{m.entity_type}: {m.entity_value}</span>
                    <span className={s.fndWhen}>{m.mention_count} mention(s)</span>
                  </div>
                  <div
                    onClick={() => navigate(`/investigations/${m.case_id}/overview`)}
                    style={{ cursor: "pointer", padding: "var(--space-2) 0", color: "var(--text-secondary)", font: "var(--type-body-sm)" }}
                  >
                    Detected in <strong style={{ color: "var(--text-primary)" }}>{m.case_title}</strong>
                    <span className="t-mono-xs" style={{ color: "var(--text-muted)", marginLeft: 8 }}>{m.case_number}</span>
                    {m.crime_type && <span className="t-mono-xs" style={{ color: "var(--text-secondary)", marginLeft: 8 }}>· {m.crime_type}</span>}
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <div style={{
              padding: "var(--space-10) var(--space-6)", textAlign: "center",
              background: "var(--surface-1)", border: "1px dashed var(--line-strong)",
              borderRadius: "var(--radius-card)",
            }}>
              <div style={{ font: "var(--type-mono-xs)", color: "var(--intel)", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: "var(--space-2)" }}>
                Correlation Engine
              </div>
              <p className="measure" style={{ color: "var(--text-secondary)", font: "var(--type-body-sm)", margin: "0 auto" }}>
                No cross-case findings yet. Findings appear as shared entities are detected across registered investigations.
              </p>
            </div>
          )}
        </Block>
      )}
    </div>
  );
}
