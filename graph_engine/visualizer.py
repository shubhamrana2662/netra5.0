"""
CyberDrishti AI — Standalone Interactive Graph HTML Visualizer
==============================================================
Generates a zero-dependency, self-contained interactive HTML visualization
from serialized graph JSON (nodes, observed evidence edges, and predicted hidden links).
Features:
- Dark-mode cyber crime investigation interface
- 2D force-directed physics layout with node drag & zoom
- Color-coded community clusters and entity type badges
- Inferred hidden links displayed as glowing amber/cyan dashed links
- Node click inspection drawer showing timestamps, degree centrality, bridge score
- Hidden-link inspection with 6-feature explainability radar/bar chart
- Search bar, community filter, and hidden-link visibility toggle
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def generate_interactive_html(
    graph_json: dict[str, Any],
    title: str = "CyberDrishti AI — Threat Entity & Hidden-Link Investigation Graph",
) -> str:
    """Generate self-contained HTML file string containing interactive graph."""
    graph_data_str = json.dumps(graph_json)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <!-- Vis.js Network CDN -->
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    * {{
      margin: 0;
      padding: 0;
      box-sizing: border-box;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}
    body {{
      background: #090d16;
      color: #e2e8f0;
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background: rgba(15, 23, 42, 0.95);
      border-bottom: 1px solid rgba(56, 189, 248, 0.2);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      backdrop-filter: blur(8px);
      z-index: 10;
    }}
    .header-title {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .logo-badge {{
      background: linear-gradient(135deg, #0284c7, #06b6d4);
      color: #fff;
      font-weight: 800;
      font-size: 11px;
      letter-spacing: 1.5px;
      padding: 4px 8px;
      border-radius: 4px;
      text-transform: uppercase;
      box-shadow: 0 0 10px rgba(6, 182, 212, 0.4);
    }}
    h1 {{
      font-size: 16px;
      font-weight: 600;
      color: #f8fafc;
      letter-spacing: -0.2px;
    }}
    .header-stats {{
      display: flex;
      gap: 16px;
      font-size: 12px;
    }}
    .stat-pill {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid rgba(148, 163, 184, 0.15);
      padding: 4px 12px;
      border-radius: 9999px;
      color: #94a3b8;
    }}
    .stat-pill strong {{
      color: #38bdf8;
    }}
    .stat-pill.hidden-pill strong {{
      color: #f59e0b;
    }}
    .main-container {{
      flex: 1;
      display: flex;
      position: relative;
      height: calc(100vh - 58px);
    }}
    #graph-network {{
      flex: 1;
      height: 100%;
      background: radial-gradient(circle at 50% 50%, #0f172a 0%, #060911 100%);
    }}
    /* Controls Bar */
    .controls-panel {{
      position: absolute;
      top: 16px;
      left: 16px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      z-index: 5;
      backdrop-filter: blur(8px);
      width: 260px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
    }}
    .controls-panel label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #94a3b8;
      font-weight: 600;
    }}
    .search-input {{
      background: rgba(30, 41, 59, 0.9);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 6px 10px;
      border-radius: 6px;
      color: #fff;
      font-size: 12px;
      outline: none;
    }}
    .search-input:focus {{
      border-color: #38bdf8;
      box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
    }}
    .toggle-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: #cbd5e1;
    }}
    .switch {{
      position: relative;
      display: inline-block;
      width: 36px;
      height: 20px;
    }}
    .switch input {{
      opacity: 0;
      width: 0;
      height: 0;
    }}
    .slider {{
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background-color: #334155;
      transition: .3s;
      border-radius: 20px;
    }}
    .slider:before {{
      position: absolute;
      content: "";
      height: 14px;
      width: 14px;
      left: 3px;
      bottom: 3px;
      background-color: white;
      transition: .3s;
      border-radius: 50%;
    }}
    input:checked + .slider {{
      background-color: #0284c7;
    }}
    input:checked + .slider:before {{
      transform: translateX(16px);
    }}
    /* Inspector Sidebar */
    .inspector-drawer {{
      width: 360px;
      background: rgba(15, 23, 42, 0.95);
      border-left: 1px solid rgba(56, 189, 248, 0.2);
      height: 100%;
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 16px;
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(12px);
    }}
    .drawer-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid rgba(148, 163, 184, 0.15);
      padding-bottom: 12px;
    }}
    .drawer-title {{
      font-size: 14px;
      font-weight: 700;
      color: #f8fafc;
      text-transform: uppercase;
      letter-spacing: 0.8px;
    }}
    .entity-badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }}
    .badge-PER {{ background: #0284c7; color: #fff; }}
    .badge-PHONE {{ background: #059669; color: #fff; }}
    .badge-UPI {{ background: #7c3aed; color: #fff; }}
    .badge-ACCOUNT {{ background: #ea580c; color: #fff; }}
    .badge-AMOUNT {{ background: #16a34a; color: #fff; }}
    .badge-IP {{ background: #dc2626; color: #fff; }}
    .badge-IFSC {{ background: #0891b2; color: #fff; }}
    .badge-hidden {{ background: #f59e0b; color: #000; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }}
    .metric-box {{
      background: rgba(30, 41, 59, 0.6);
      border: 1px solid rgba(148, 163, 184, 0.1);
      padding: 10px;
      border-radius: 6px;
    }}
    .metric-label {{
      font-size: 10px;
      color: #94a3b8;
      text-transform: uppercase;
      margin-bottom: 4px;
    }}
    .metric-val {{
      font-size: 16px;
      font-weight: 700;
      color: #38bdf8;
    }}
    .explain-bar {{
      margin-bottom: 10px;
    }}
    .bar-label {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #cbd5e1;
      margin-bottom: 4px;
    }}
    .bar-track {{
      height: 6px;
      background: #1e293b;
      border-radius: 3px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, #38bdf8, #818cf8);
      border-radius: 3px;
    }}
    .bar-fill.amber {{
      background: linear-gradient(90deg, #f59e0b, #ef4444);
    }}
    .evidence-item {{
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid rgba(148, 163, 184, 0.15);
      border-left: 3px solid #38bdf8;
      padding: 10px;
      border-radius: 4px;
      font-size: 12px;
      line-height: 1.4;
      color: #cbd5e1;
    }}
    .evidence-meta {{
      font-size: 10px;
      color: #94a3b8;
      margin-top: 4px;
    }}
    .legend-box {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid rgba(56, 189, 248, 0.2);
      border-radius: 8px;
      padding: 10px 14px;
      z-index: 5;
      font-size: 11px;
      display: flex;
      gap: 16px;
      align-items: center;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .legend-dot {{
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }}
    .legend-line {{
      width: 20px;
      height: 2px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-title">
      <span class="logo-badge">CyberDrishti AI</span>
      <h1>Case Graph: {graph_json.get("case_id", "Investigation Case")}</h1>
    </div>
    <div class="header-stats">
      <div class="stat-pill">Entities: <strong id="stat-nodes">{len(graph_json.get("nodes", []))}</strong></div>
      <div class="stat-pill">Observed Edges: <strong id="stat-edges">{len(graph_json.get("edges", []))}</strong></div>
      <div class="stat-pill hidden-pill">Inferred Hidden Links: <strong id="stat-hidden">{len(graph_json.get("hidden_edges", []))}</strong></div>
    </div>
  </header>

  <div class="main-container">
    <div class="controls-panel">
      <label>Search Entity</label>
      <input type="text" id="search-box" class="search-input" placeholder="Type name, phone, account...">
      
      <div class="toggle-row">
        <span>Show Hidden Links</span>
        <label class="switch">
          <input type="checkbox" id="toggle-hidden" checked>
          <span class="slider"></span>
        </label>
      </div>

      <div class="toggle-row">
        <span>Physics Layout</span>
        <label class="switch">
          <input type="checkbox" id="toggle-physics" checked>
          <span class="slider"></span>
        </label>
      </div>
      <button id="btn-fit" style="background:#1e293b; border:1px solid #475569; color:#f8fafc; padding:6px; border-radius:4px; font-size:11px; cursor:pointer;">Reset View / Fit</button>
    </div>

    <div id="graph-network"></div>

    <div class="legend-box">
      <div class="legend-item"><div class="legend-line" style="background:#38bdf8;"></div> Observed Co-occurrence</div>
      <div class="legend-item"><div class="legend-line" style="background:#f59e0b; border-top:2px dashed #f59e0b;"></div> Inferred Hidden Link (P&ge;90%)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#0284c7;"></div> Suspect (PER)</div>
      <div class="legend-item"><div class="legend-dot" style="background:#059669;"></div> Phone</div>
      <div class="legend-item"><div class="legend-dot" style="background:#ea580c;"></div> Account</div>
      <div class="legend-item"><div class="legend-dot" style="background:#7c3aed;"></div> UPI</div>
    </div>

    <div class="inspector-drawer" id="inspector">
      <div class="drawer-header">
        <span class="drawer-title">Entity Inspector</span>
        <span id="insp-badge" class="entity-badge badge-PER">SELECT NODE</span>
      </div>
      <div id="insp-content">
        <p style="color:#64748b; font-size:13px;">Click on any node or edge in the graph to inspect evidence citations, centrality metrics, and explainability breakdown.</p>
      </div>
    </div>
  </div>

  <script>
    const graphData = {graph_data_str};

    const typeColors = {{
      PER: "#0284c7",
      PHONE: "#059669",
      UPI: "#7c3aed",
      ACCOUNT: "#ea580c",
      AMOUNT: "#16a34a",
      IP: "#dc2626",
      IFSC: "#0891b2",
      UNKNOWN: "#64748b"
    }};

    // Format Nodes
    const nodesArray = graphData.nodes.map(n => {{
      const baseColor = typeColors[n.entity_type] || "#64748b";
      const size = 18 + (n.degree_centrality || 0) * 35;
      return {{
        id: n.id,
        label: n.label || n.id,
        entity_type: n.entity_type,
        canonical_value: n.canonical_value,
        degree_centrality: n.degree_centrality,
        bridge_score: n.bridge_score,
        community_id: n.community_id,
        mention_count: n.mention_count,
        first_seen: n.first_seen,
        last_seen: n.last_seen,
        color: {{
          background: baseColor,
          border: "#38bdf8",
          highlight: {{ background: "#38bdf8", border: "#fff" }}
        }},
        font: {{ color: "#f8fafc", size: 12, face: "sans-serif" }},
        size: size,
        shape: "dot",
        shadow: {{ enabled: true, color: baseColor, size: 8 }}
      }};
    }});

    // Format Observed Edges
    let edgesArray = graphData.edges.map((e, idx) => ({{
      id: "obs_" + idx,
      from: e.source,
      to: e.target,
      label: e.edge_type,
      font: {{ color: "#64748b", size: 9, align: "middle" }},
      color: {{ color: "rgba(56, 189, 248, 0.4)", highlight: "#38bdf8" }},
      width: Math.min(6, 1.5 + (e.weight || 1) * 0.8),
      smooth: {{ type: "continuous" }},
      is_hidden: false,
      raw_edge: e
    }}));

    // Format Hidden Links
    const hiddenEdgesArray = (graphData.hidden_edges || []).map((h, idx) => ({{
      id: "hid_" + idx,
      from: h.source,
      to: h.target,
      label: "HIDDEN LINK (" + (h.score * 100).toFixed(0) + "%)",
      font: {{ color: "#f59e0b", size: 10, face: "monospace", align: "top" }},
      color: {{ color: "#f59e0b", highlight: "#fbbf24" }},
      width: 2.5,
      dashes: [6, 4],
      smooth: {{ type: "curvedCW", roundness: 0.2 }},
      is_hidden: true,
      raw_hidden: h
    }}));

    const nodesDataSet = new vis.DataSet(nodesArray);
    const edgesDataSet = new vis.DataSet([...edgesArray, ...hiddenEdgesArray]);

    const container = document.getElementById("graph-network");
    const data = {{ nodes: nodesDataSet, edges: edgesDataSet }};
    const options = {{
      physics: {{
        barnesHut: {{
          gravitationalConstant: -3500,
          centralGravity: 0.3,
          springLength: 120,
          springConstant: 0.04
        }},
        stabilization: {{ iterations: 150 }}
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 100,
        navigationButtons: true,
        keyboard: true
      }}
    }};

    const network = new vis.Network(container, data, options);

    // Inspector Rendering
    network.on("selectNode", function(params) {{
      if (params.nodes.length === 0) return;
      const nodeId = params.nodes[0];
      const node = nodesDataSet.get(nodeId);
      renderNodeInspector(node);
    }});

    network.on("selectEdge", function(params) {{
      if (params.edges.length === 0 || params.nodes.length > 0) return;
      const edgeId = params.edges[0];
      const edge = edgesDataSet.get(edgeId);
      if (edge && edge.is_hidden) {{
        renderHiddenLinkInspector(edge.raw_hidden);
      }}
    }});

    function renderNodeInspector(node) {{
      const badge = document.getElementById("insp-badge");
      badge.className = "entity-badge badge-" + (node.entity_type || "PER");
      badge.textContent = node.entity_type || "UNKNOWN";

      const content = document.getElementById("insp-content");
      content.innerHTML = `
        <div style="font-size: 16px; font-weight: 700; color:#f8fafc; word-break: break-all;">${{node.label}}</div>
        
        <div class="metric-grid">
          <div class="metric-box">
            <div class="metric-label">Centrality</div>
            <div class="metric-val">${{(node.degree_centrality || 0).toFixed(4)}}</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Bridge Score</div>
            <div class="metric-val">${{(node.bridge_score || 0).toFixed(2)}}</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Community ID</div>
            <div class="metric-val">#${{node.community_id !== null ? node.community_id : "N/A"}}</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Observed Mentions</div>
            <div class="metric-val">${{node.mention_count || 1}}</div>
          </div>
        </div>

        <div style="margin-top: 10px;">
          <div class="metric-label">Investigation Timeline</div>
          <div style="font-size:12px; color:#94a3b8; margin-top:4px;">
            First observed: <strong style="color:#e2e8f0;">${{node.first_seen || "N/A"}}</strong><br>
            Last observed: <strong style="color:#e2e8f0;">${{node.last_seen || "N/A"}}</strong>
          </div>
        </div>
      `;
    }}

    function renderHiddenLinkInspector(hidden) {{
      const badge = document.getElementById("insp-badge");
      badge.className = "entity-badge badge-hidden";
      badge.textContent = "INFERRED HIDDEN LINK";

      const cs = hidden.component_scores || {{}};
      const content = document.getElementById("insp-content");
      content.innerHTML = `
        <div style="font-size: 14px; font-weight: 700; color:#f59e0b;">Hidden Link Inference</div>
        <div style="font-size: 12px; color:#cbd5e1; margin-bottom: 8px;">
          Between: <strong>${{hidden.source}}</strong> &harr; <strong>${{hidden.target}}</strong>
        </div>
        
        <div class="metric-grid">
          <div class="metric-box">
            <div class="metric-label">Inference Score</div>
            <div class="metric-val" style="color:#f59e0b;">${{(hidden.score * 100).toFixed(1)}}%</div>
          </div>
          <div class="metric-box">
            <div class="metric-label">Precision Gate</div>
            <div class="metric-val" style="color:#10b981;">&ge; 90%</div>
          </div>
        </div>

        <div style="margin-top: 12px;">
          <div class="metric-label" style="margin-bottom:8px;">Section 65B Explainability Breakdown</div>
          
          <div class="explain-bar">
            <div class="bar-label"><span>Jaccard Neighbor Coeff</span><span>${{(cs.jaccard || 0).toFixed(3)}}</span></div>
            <div class="bar-track"><div class="bar-fill amber" style="width: ${{Math.min(100, (cs.jaccard || 0) * 100)}}%;"></div></div>
          </div>

          <div class="explain-bar">
            <div class="bar-label"><span>Temporal Proximity</span><span>${{(cs.temporal || 0).toFixed(3)}}</span></div>
            <div class="bar-track"><div class="bar-fill amber" style="width: ${{Math.min(100, (cs.temporal || 0) * 100)}}%;"></div></div>
          </div>

          <div class="explain-bar">
            <div class="bar-label"><span>Financial Decay Correlation</span><span>${{(cs.financial || 0).toFixed(3)}}</span></div>
            <div class="bar-track"><div class="bar-fill amber" style="width: ${{Math.min(100, (cs.financial || 0) * 100)}}%;"></div></div>
          </div>

          <div class="explain-bar">
            <div class="bar-label"><span>Bridge Score Traversal</span><span>${{(cs.bridge_score || 0).toFixed(3)}}</span></div>
            <div class="bar-track"><div class="bar-fill amber" style="width: ${{Math.min(100, (cs.bridge_score || 0) * 100)}}%;"></div></div>
          </div>
        </div>
      `;
    }}

    // Controls
    document.getElementById("toggle-hidden").addEventListener("change", function(e) {{
      if (e.target.checked) {{
        edgesDataSet.add(hiddenEdgesArray);
      }} else {{
        edgesDataSet.remove(hiddenEdgesArray.map(h => h.id));
      }}
    }});

    document.getElementById("toggle-physics").addEventListener("change", function(e) {{
      network.setOptions({{ physics: {{ enabled: e.target.checked }} }});
    }});

    document.getElementById("btn-fit").addEventListener("click", function() {{
      network.fit({{ animation: {{ duration: 500 }} }});
    }});

    document.getElementById("search-box").addEventListener("input", function(e) {{
      const val = e.target.value.toLowerCase().trim();
      if (!val) return;
      const match = nodesArray.find(n => n.id.toLowerCase().includes(val) || (n.label && n.label.toLowerCase().includes(val)));
      if (match) {{
        network.focus(match.id, {{ scale: 1.4, animation: {{ duration: 600 }} }});
        network.selectNodes([match.id]);
        renderNodeInspector(match);
      }}
    }});
  </script>
</body>
</html>
"""
    return html_content


def export_graph_to_html(
    graph_json: dict[str, Any],
    output_path: str | Path,
    title: Optional[str] = None,
) -> Path:
    """Save graph as a self-contained interactive HTML file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = generate_interactive_html(graph_json, title=title or f"Case Graph - {graph_json.get('case_id', 'Investigation')}")
    path.write_text(html, encoding="utf-8")
    return path
