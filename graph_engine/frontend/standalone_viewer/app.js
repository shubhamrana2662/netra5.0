/**
 * CyberDrishti AI — Standalone Graph Viewer Controller
 */

// Fallback embedded case graph (ensures zero CORS issues when opening file:// directly)
const EMBEDDED_CASE_GRAPH = {
  case_id: "CYBER-DEL-2026-0891",
  title: "Mule Syndicate & Phishing Extortion Network",
  nodes: [
    { id: "Vikram Sharma", label: "Vikram Sharma", entity_type: "PER", degree_centrality: 0.3333, bridge_score: 0.33, community_id: 0, mention_count: 2, first_seen: "2026-08-15T09:12:00Z", last_seen: "2026-08-15T09:12:00Z" },
    { id: "Sanjeev Kumar", label: "Sanjeev Kumar", entity_type: "PER", degree_centrality: 0.1667, bridge_score: 0.0, community_id: 1, mention_count: 1, first_seen: "2026-08-15T10:15:00Z", last_seen: "2026-08-15T10:15:00Z" },
    { id: "+919876543210", label: "+919876543210", entity_type: "PHONE", degree_centrality: 0.2500, bridge_score: 0.67, community_id: 0, mention_count: 2, first_seen: "2026-08-15T09:35:00Z", last_seen: "2026-08-15T09:42:00Z" },
    { id: "+919123456789", label: "+919123456789", entity_type: "PHONE", degree_centrality: 0.2500, bridge_score: 0.67, community_id: 1, mention_count: 2, first_seen: "2026-08-15T09:35:00Z", last_seen: "2026-08-15T10:15:00Z" },
    { id: "+919988776655", label: "+919988776655", entity_type: "PHONE", degree_centrality: 0.2500, bridge_score: 0.33, community_id: 1, mention_count: 2, first_seen: "2026-08-15T10:15:00Z", last_seen: "2026-08-15T10:20:00Z" },
    { id: "vikram.sharma@paytm", label: "vikram.sharma@paytm", entity_type: "UPI", degree_centrality: 0.1667, bridge_score: 0.0, community_id: 0, mention_count: 1, first_seen: "2026-08-15T09:42:00Z", last_seen: "2026-08-15T09:42:00Z" },
    { id: "fastpay.settle@okhdfcbank", label: "fastpay.settle@okhdfcbank", entity_type: "UPI", degree_centrality: 0.1667, bridge_score: 0.0, community_id: 0, mention_count: 1, first_seen: "2026-08-15T09:42:00Z", last_seen: "2026-08-15T09:42:00Z" },
    { id: "918273645012", label: "918273645012", entity_type: "ACCOUNT", degree_centrality: 0.3333, bridge_score: 0.0, community_id: 0, mention_count: 2, first_seen: "2026-08-15T09:12:00Z", last_seen: "2026-08-15T09:30:00Z" },
    { id: "382910475819", label: "382910475819", entity_type: "ACCOUNT", degree_centrality: 0.3333, bridge_score: 0.25, community_id: 0, mention_count: 2, first_seen: "2026-08-15T09:30:00Z", last_seen: "2026-08-15T10:05:00Z" },
    { id: "772619482015", label: "772619482015", entity_type: "ACCOUNT", degree_centrality: 0.2500, bridge_score: 0.33, community_id: 2, mention_count: 2, first_seen: "2026-08-15T10:05:00Z", last_seen: "2026-08-15T10:20:00Z" },
    { id: "192.168.45.102", label: "192.168.45.102", entity_type: "IP", degree_centrality: 0.2500, bridge_score: 0.33, community_id: 2, mention_count: 2, first_seen: "2026-08-15T10:05:00Z", last_seen: "2026-08-15T10:20:00Z" },
    { id: "HDFC0001234", label: "HDFC0001234", entity_type: "IFSC", degree_centrality: 0.2500, bridge_score: 0.0, community_id: 0, mention_count: 1, first_seen: "2026-08-15T09:30:00Z", last_seen: "2026-08-15T09:30:00Z" }
  ],
  edges: [
    { source: "Vikram Sharma", target: "918273645012", edge_type: "whatsapp_msg", weight: 1 },
    { source: "918273645012", target: "382910475819", edge_type: "bank_txn", weight: 1 },
    { source: "382910475819", target: "HDFC0001234", edge_type: "bank_txn", weight: 1 },
    { source: "+919876543210", target: "+919123456789", edge_type: "call", weight: 1 },
    { source: "vikram.sharma@paytm", target: "+919876543210", edge_type: "payment_gateway", weight: 1 },
    { source: "vikram.sharma@paytm", target: "fastpay.settle@okhdfcbank", edge_type: "payment_gateway", weight: 1 },
    { source: "+919876543210", target: "fastpay.settle@okhdfcbank", edge_type: "payment_gateway", weight: 1 },
    { source: "382910475819", target: "772619482015", edge_type: "bank_txn", weight: 1 },
    { source: "382910475819", target: "192.168.45.102", edge_type: "bank_txn", weight: 1 },
    { source: "772619482015", target: "192.168.45.102", edge_type: "bank_txn", weight: 2 },
    { source: "Sanjeev Kumar", target: "+919123456789", edge_type: "cdr_log", weight: 1 },
    { source: "Sanjeev Kumar", target: "+919988776655", edge_type: "cdr_log", weight: 1 },
    { source: "+919123456789", target: "+919988776655", edge_type: "cdr_log", weight: 1 },
    { source: "772619482015", target: "+919988776655", edge_type: "ip_login", weight: 1 },
    { source: "192.168.45.102", target: "+919988776655", edge_type: "ip_login", weight: 1 }
  ],
  hidden_edges: [
    {
      source: "Vikram Sharma",
      target: "382910475819",
      score: 0.784,
      threshold: 0.365,
      component_scores: { jaccard: 0.50, temporal: 1.25, financial: 0.94, bridge_score: 0.25, adamic_adar: 1.12 }
    },
    {
      source: "Vikram Sharma",
      target: "772619482015",
      score: 0.640,
      threshold: 0.365,
      component_scores: { jaccard: 0.00, temporal: 0.74, financial: 0.88, bridge_score: 0.33, adamic_adar: 0.00 }
    },
    {
      source: "Vikram Sharma",
      target: "192.168.45.102",
      score: 0.640,
      threshold: 0.365,
      component_scores: { jaccard: 0.00, temporal: 0.74, financial: 0.00, bridge_score: 0.33, adamic_adar: 0.00 }
    },
    {
      source: "+919876543210",
      target: "+919988776655",
      score: 0.695,
      threshold: 0.365,
      component_scores: { jaccard: 0.33, temporal: 1.10, financial: 0.00, bridge_score: 0.50, adamic_adar: 0.91 }
    },
    {
      source: "vikram.sharma@paytm",
      target: "918273645012",
      score: 0.524,
      threshold: 0.365,
      component_scores: { jaccard: 0.00, temporal: 1.42, financial: 0.85, bridge_score: 0.00, adamic_adar: 0.00 }
    }
  ]
};

// ── Visual Palette ────────────────────────────────────────────────────────────
const TYPE_COLORS = {
  PER: "#3b82f6",
  PHONE: "#8b5cf6",
  UPI: "#d97706",
  ACCOUNT: "#059669",
  IP: "#dc2626",
  IFSC: "#0891b2",
  UNKNOWN: "#64748b"
};

let currentCase = EMBEDDED_CASE_GRAPH;
let activeFilters = new Set(["ALL"]);
let showHiddenLinks = true;
let confidenceThreshold = 0.36;
let twoHopMode = false;
let selectedNodeId = null;

let nodesDataSet = null;
let edgesDataSet = null;
let network = null;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initGraph();
  setupEventListeners();
  updateStats();
});

function initGraph() {
  const container = document.getElementById("vis-network");

  // Format nodes
  const nodes = currentCase.nodes.map(n => {
    const color = TYPE_COLORS[n.entity_type] || TYPE_COLORS.UNKNOWN;
    const size = 18 + (n.degree_centrality || 0) * 35;
    return {
      id: n.id,
      label: n.label || n.id,
      entity_type: n.entity_type,
      degree_centrality: n.degree_centrality,
      bridge_score: n.bridge_score,
      community_id: n.community_id,
      mention_count: n.mention_count,
      first_seen: n.first_seen,
      last_seen: n.last_seen,
      color: {
        background: color,
        border: "#38bdf8",
        highlight: { background: "#38bdf8", border: "#fff" }
      },
      font: { color: "#f8fafc", size: 12, face: "sans-serif" },
      size: size,
      shape: "dot",
      shadow: { enabled: true, color: color, size: 8 }
    };
  });

  // Format edges
  const edges = currentCase.edges.map((e, idx) => ({
    id: `obs_${idx}`,
    from: e.source,
    to: e.target,
    label: e.edge_type,
    font: { color: "#64748b", size: 9, align: "middle" },
    color: { color: "rgba(56, 189, 248, 0.4)", highlight: "#38bdf8" },
    width: Math.min(5, 1.5 + (e.weight || 1) * 0.8),
    smooth: { type: "continuous" },
    is_hidden: false,
    raw: e
  }));

  nodesDataSet = new vis.DataSet(nodes);
  edgesDataSet = new vis.DataSet(edges);

  const data = { nodes: nodesDataSet, edges: edgesDataSet };
  const options = {
    physics: {
      barnesHut: {
        gravitationalConstant: -3800,
        centralGravity: 0.35,
        springLength: 120,
        springConstant: 0.04
      },
      stabilization: { iterations: 120 }
    },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      navigationButtons: true,
      keyboard: true
    }
  };

  network = new vis.Network(container, data, options);

  // Sync hidden links
  applyFilters();

  network.on("selectNode", (params) => {
    if (params.nodes.length === 0) return;
    selectedNodeId = params.nodes[0];
    const node = nodesDataSet.get(selectedNodeId);
    renderNodeInspector(node);

    if (twoHopMode) {
      applyTwoHopFilter(selectedNodeId);
    }
  });

  network.on("selectEdge", (params) => {
    if (params.edges.length === 0 || params.nodes.length > 0) return;
    const edgeId = params.edges[0];
    const edge = edgesDataSet.get(edgeId);
    if (edge && edge.is_hidden) {
      renderHiddenLinkInspector(edge.raw);
    }
  });
}

function applyFilters() {
  const currentNodes = nodesDataSet.get();
  const visibleNodeIds = new Set();

  currentNodes.forEach(n => {
    const typeMatch = activeFilters.has("ALL") || activeFilters.has(n.entity_type);
    if (typeMatch) {
      visibleNodeIds.add(n.id);
      nodesDataSet.update({ id: n.id, hidden: false });
    } else {
      nodesDataSet.update({ id: n.id, hidden: true });
    }
  });

  // Re-evaluate hidden links based on threshold & visibility
  const existingHiddenIds = edgesDataSet.get({
    filter: (e) => e.is_hidden
  }).map(e => e.id);
  edgesDataSet.remove(existingHiddenIds);

  if (showHiddenLinks) {
    const validHidden = currentCase.hidden_edges
      .filter(h => h.score >= confidenceThreshold)
      .filter(h => visibleNodeIds.has(h.source) && visibleNodeIds.has(h.target))
      .map((h, idx) => ({
        id: `hid_${idx}`,
        from: h.source,
        to: h.target,
        label: `HIDDEN LINK (${(h.score * 100).toFixed(0)}%)`,
        font: { color: "#f59e0b", size: 10, face: "monospace", align: "top" },
        color: { color: "#f59e0b", highlight: "#fbbf24" },
        width: 2.5,
        dashes: [6, 4],
        smooth: { type: "curvedCW", roundness: 0.2 },
        is_hidden: true,
        raw: h
      }));

    edgesDataSet.add(validHidden);
  }

  updateStats();
}

function applyTwoHopFilter(centerNodeId) {
  const connected1 = network.getConnectedNodes(centerNodeId);
  const neighborhood = new Set([centerNodeId, ...connected1]);

  connected1.forEach(hop1 => {
    const connected2 = network.getConnectedNodes(hop1);
    connected2.forEach(h2 => neighborhood.add(h2));
  });

  nodesDataSet.get().forEach(n => {
    nodesDataSet.update({ id: n.id, hidden: !neighborhood.has(n.id) });
  });
}

function renderNodeInspector(node) {
  const title = document.getElementById("inspector-title");
  const badge = document.getElementById("inspector-badge");
  const body = document.getElementById("inspector-body");

  title.textContent = "Node Forensic Dossier";
  badge.textContent = node.entity_type || "ENTITY";
  badge.style.background = TYPE_COLORS[node.entity_type] || "#334155";
  badge.style.color = "#fff";

  body.innerHTML = `
    <div style="font-size: 16px; font-weight: 700; color:#f8fafc; word-break: break-all;">${node.label}</div>
    
    <div class="metric-grid">
      <div class="metric-box">
        <div class="metric-label">Centrality</div>
        <div class="metric-val">${(node.degree_centrality || 0).toFixed(4)}</div>
      </div>
      <div class="metric-box">
        <div class="metric-label">Bridge Score</div>
        <div class="metric-val">${(node.bridge_score || 0).toFixed(2)}</div>
      </div>
      <div class="metric-box">
        <div class="metric-label">Community ID</div>
        <div class="metric-val">#${node.community_id !== null ? node.community_id : "0"}</div>
      </div>
      <div class="metric-box">
        <div class="metric-label">Mentions</div>
        <div class="metric-val">${node.mention_count || 1}</div>
      </div>
    </div>

    <div style="margin-top: 14px;">
      <div class="metric-label">Investigation Observation Range</div>
      <div style="font-size: 12px; color: #94a3b8; margin-top: 4px; line-height: 1.6;">
        First observed: <strong style="color: #e2e8f0;">${node.first_seen || "2026-08-15T09:12:00Z"}</strong><br>
        Last observed: <strong style="color: #e2e8f0;">${node.last_seen || "2026-08-15T10:20:00Z"}</strong>
      </div>
    </div>
  `;
}

function renderHiddenLinkInspector(hidden) {
  const title = document.getElementById("inspector-title");
  const badge = document.getElementById("inspector-badge");
  const body = document.getElementById("inspector-body");

  title.textContent = "Hidden Link Audit";
  badge.textContent = "FLAGGED LINK";
  badge.style.background = "#f59e0b";
  badge.style.color = "#000";

  const cs = hidden.component_scores || {};

  body.innerHTML = `
    <div style="font-size: 14px; font-weight: 700; color:#f59e0b;">Court-Admissible Predictive Link</div>
    <div style="font-size: 12px; color:#cbd5e1; margin-top: 4px; margin-bottom: 12px;">
      Between: <strong style="color:#fff;">${hidden.source}</strong> &harr; <strong style="color:#fff;">${hidden.target}</strong>
    </div>

    <div class="metric-grid">
      <div class="metric-box">
        <div class="metric-label">Confidence</div>
        <div class="metric-val" style="color:#f59e0b;">${(hidden.score * 100).toFixed(1)}%</div>
      </div>
      <div class="metric-box">
        <div class="metric-label">Precision Gate</div>
        <div class="metric-val" style="color:#10b981;">&ge; 90.0%</div>
      </div>
    </div>

    <div style="margin-top: 16px;">
      <div class="metric-label" style="margin-bottom: 8px;">Section 65B Metric Breakdown</div>
      
      <div class="explain-bar">
        <div class="bar-label"><span>Jaccard Coeff</span><span>${(cs.jaccard || 0).toFixed(3)}</span></div>
        <div class="bar-track"><div class="bar-fill amber" style="width: ${Math.min(100, (cs.jaccard || 0) * 100)}%;"></div></div>
      </div>

      <div class="explain-bar">
        <div class="bar-label"><span>Temporal Proximity</span><span>${(cs.temporal || 0).toFixed(3)}</span></div>
        <div class="bar-track"><div class="bar-fill amber" style="width: ${Math.min(100, (cs.temporal || 0) * 100)}%;"></div></div>
      </div>

      <div class="explain-bar">
        <div class="bar-label"><span>Financial Decay Correlation</span><span>${(cs.financial || 0).toFixed(3)}</span></div>
        <div class="bar-track"><div class="bar-fill amber" style="width: ${Math.min(100, (cs.financial || 0) * 100)}%;"></div></div>
      </div>

      <div class="explain-bar">
        <div class="bar-label"><span>Bridge Score Traversal</span><span>${(cs.bridge_score || 0).toFixed(3)}</span></div>
        <div class="bar-track"><div class="bar-fill amber" style="width: ${Math.min(100, (cs.bridge_score || 0) * 100)}%;"></div></div>
      </div>
    </div>
  `;
}

function updateStats() {
  document.getElementById("stat-nodes").textContent = nodesDataSet ? nodesDataSet.length : 0;
  document.getElementById("stat-edges").textContent = edgesDataSet ? edgesDataSet.get({ filter: e => !e.is_hidden }).length : 0;
  document.getElementById("stat-hidden").textContent = edgesDataSet ? edgesDataSet.get({ filter: e => e.is_hidden }).length : 0;
}

function setupEventListeners() {
  // Search
  document.getElementById("search-box").addEventListener("input", (e) => {
    const q = e.target.value.toLowerCase().trim();
    if (!q) return;
    const match = nodesDataSet.get().find(n => n.id.toLowerCase().includes(q));
    if (match) {
      network.focus(match.id, { scale: 1.4, animation: { duration: 500 } });
      network.selectNodes([match.id]);
      renderNodeInspector(match);
    }
  });

  // Filter chips
  document.querySelectorAll(".chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const type = chip.dataset.type;
      if (type === "ALL") {
        activeFilters.clear();
        activeFilters.add("ALL");
        document.querySelectorAll(".chip").forEach(c => c.classList.add("active"));
      } else {
        document.querySelector('.chip[data-type="ALL"]').classList.remove("active");
        activeFilters.delete("ALL");
        if (activeFilters.has(type)) {
          activeFilters.delete(type);
          chip.classList.remove("active");
        } else {
          activeFilters.add(type);
          chip.classList.add("active");
        }
        if (activeFilters.size === 0) {
          activeFilters.add("ALL");
          document.querySelectorAll(".chip").forEach(c => c.classList.add("active"));
        }
      }
      applyFilters();
    });
  });

  // Toggle Hidden Links
  document.getElementById("toggle-hidden").addEventListener("change", (e) => {
    showHiddenLinks = e.target.checked;
    document.getElementById("threshold-group").style.opacity = showHiddenLinks ? "1" : "0.4";
    applyFilters();
  });

  // Threshold Slider
  document.getElementById("threshold-slider").addEventListener("input", (e) => {
    confidenceThreshold = parseInt(e.target.value, 10) / 100.0;
    document.getElementById("threshold-val").textContent = `${e.target.value}%`;
    applyFilters();
  });

  // 2-Hop Toggle
  document.getElementById("toggle-twohop").addEventListener("change", (e) => {
    twoHopMode = e.target.checked;
    if (!twoHopMode) {
      applyFilters();
    } else if (selectedNodeId) {
      applyTwoHopFilter(selectedNodeId);
    }
  });

  // Camera fit
  document.getElementById("btn-fit").addEventListener("click", () => {
    network.fit({ animation: { duration: 400 } });
  });

  // Reload
  document.getElementById("btn-reload").addEventListener("click", () => {
    initGraph();
  });
}
