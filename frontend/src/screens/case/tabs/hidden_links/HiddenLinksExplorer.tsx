import React, { useState, useMemo } from 'react';
import { InferredHiddenLink } from '../graphEngine';
import styles from './hiddenLinks.module.css';

interface HiddenLinksExplorerProps {
  links: InferredHiddenLink[];
  onLocateInGraph: (sourceId: string, targetId: string) => void;
  onInvestigateIn3D: (sourceId: string, targetId: string) => void;
  onClose?: () => void;
}

export const HiddenLinksExplorer: React.FC<HiddenLinksExplorerProps> = ({
  links,
  onLocateInGraph,
  onInvestigateIn3D,
  onClose
}) => {
  const [filter, setFilter] = useState<'all' | 'cross_cluster' | 'high_conf'>('all');
  const [selectedId, setSelectedId] = useState<string>(links[0]?.id || '');

  const filteredLinks = useMemo(() => {
    return links.filter(link => {
      if (filter === 'cross_cluster') return link.crossCluster;
      if (filter === 'high_conf') return link.confidence >= 80;
      return true;
    });
  }, [links, filter]);

  const activeLink = useMemo(() => {
    return links.find(l => l.id === selectedId) || filteredLinks[0] || null;
  }, [links, selectedId, filteredLinks]);

  return (
    <div className={styles.container}>
      {/* Left List Pane */}
      <div className={styles.listPane}>
        <div className={styles.listHeader}>
          <div className={styles.titleRow}>
            <span className={styles.title}>
              <span>◈</span> Inferred Relations
            </span>
            <span className={styles.badge}>{links.length} Discovered</span>
          </div>

          <div className={styles.filterPills}>
            <button
              className={`${styles.pill} ${filter === 'all' ? styles.pillActive : ''}`}
              onClick={() => setFilter('all')}
            >
              All ({links.length})
            </button>
            <button
              className={`${styles.pill} ${filter === 'cross_cluster' ? styles.pillActive : ''}`}
              onClick={() => setFilter('cross_cluster')}
            >
              Bridges ({links.filter(l => l.crossCluster).length})
            </button>
            <button
              className={`${styles.pill} ${filter === 'high_conf' ? styles.pillActive : ''}`}
              onClick={() => setFilter('high_conf')}
            >
              High Conf ({links.filter(l => l.confidence >= 80).length})
            </button>
          </div>
        </div>

        <div className={styles.linkList}>
          {filteredLinks.map(link => {
            const isSelected = link.id === (activeLink?.id || '');
            return (
              <div
                key={link.id}
                className={`${styles.linkItem} ${isSelected ? styles.linkItemActive : ''}`}
                onClick={() => setSelectedId(link.id)}
              >
                <div className={styles.itemTop}>
                  <span className={styles.itemConfidence}>{link.confidence}% CONF</span>
                  {link.crossCluster && <span className={styles.bridgeTag}>BRIDGE</span>}
                </div>
                <div className={styles.entityPair}>
                  <span>{link.sourceName}</span>
                  <span className={styles.pairArrow}>⤑</span>
                  <span>{link.targetName}</span>
                </div>
                <div className={styles.itemSnippet}>
                  {link.reasons[0]?.description || 'Multi-hop graph correlation'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Detail Pane */}
      <div className={styles.detailPane}>
        {activeLink ? (
          <>
            <div className={styles.detailHeader}>
              <div className={styles.detailTag}>
                <span>◈</span> AI HYPOTHESIS · INFERENCE CODE: {activeLink.id}
              </div>

              <div className={styles.pairHero}>
                <div className={styles.heroNode}>
                  <span className={styles.nodeKind}>{activeLink.sourceKind || 'ENTITY'}</span>
                  <span className={styles.nodeName}>{activeLink.sourceName}</span>
                </div>

                <div className={styles.heroLinkLine}>
                  <span className={styles.confPill}>{activeLink.confidence}% ANALYTICAL CONFIDENCE</span>
                  <div className={styles.dashedLine} />
                </div>

                <div className={styles.heroNode} style={{ textAlign: 'right' }}>
                  <span className={styles.nodeKind}>{activeLink.targetKind || 'ENTITY'}</span>
                  <span className={styles.nodeName}>{activeLink.targetName}</span>
                </div>
              </div>
            </div>

            <div className={styles.legalNotice}>
              LEGAL NOTICE: This is an algorithmic statistical hypothesis generated under Section 65B precision gating standards (Score: {activeLink.score} / Threshold: {activeLink.threshold}). It represents analytical probability, NOT verified factual evidence.
            </div>

            <div className={styles.sectionTitle}>
              EVIDENTIARY SIGNALS & CONTRIBUTING FACTORS ({activeLink.reasons.length})
            </div>

            <div className={styles.reasonsGrid}>
              {activeLink.reasons.map((r, i) => (
                <div key={i} className={styles.reasonCard}>
                  <div className={styles.reasonTop}>
                    <span className={styles.reasonName}>{r.title}</span>
                    <span
                      className={
                        r.contribution === 'STRONG'
                          ? styles.contribStrong
                          : r.contribution === 'MEDIUM'
                          ? styles.contribMedium
                          : styles.contribSupporting
                      }
                    >
                      {r.contribution}
                    </span>
                  </div>
                  <div className={styles.reasonDesc}>{r.description}</div>
                </div>
              ))}
            </div>

            <div className={styles.actionsRow}>
              <button
                className={`${styles.actionBtn} ${styles.actionBtnPrimary}`}
                onClick={() => onInvestigateIn3D(activeLink.sourceId, activeLink.targetId)}
              >
                <span>◉</span> INVESTIGATE IN 3D SPATIAL
              </button>
              <button
                className={`${styles.actionBtn} ${styles.actionBtnSecondary}`}
                onClick={() => onLocateInGraph(activeLink.sourceId, activeLink.targetId)}
              >
                <span>⌖</span> LOCATE IN OPERATIONAL GRAPH
              </button>
              {onClose && (
                <button
                  className={`${styles.actionBtn} ${styles.actionBtnSecondary}`}
                  onClick={onClose}
                  style={{ marginLeft: 'auto' }}
                >
                  CLOSE EXPLORER
                </button>
              )}
            </div>
          </>
        ) : (
          <div style={{ margin: 'auto', textAlign: 'center', color: '#8E929E' }}>
            No inferred links match current filter criteria.
          </div>
        )}
      </div>
    </div>
  );
};
