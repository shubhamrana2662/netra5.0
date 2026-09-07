# CyberDrishti AI — Standalone Graph Engine

A high-performance, court-admissible entity resolution and predictive hidden-link graph engine tailored for Indian cyber crime investigations.

---

## 🌟 Key Features

- **Deterministic Hard-ID Entity Extraction**: Exact regex extractors for `PHONE`, `UPI`, `ACCOUNT`, `AMOUNT`, `EMAIL`, `IP`, `IFSC`, and cell `TOWER` codes.
- **Union-Find Canonicalization**: Fast disjoint-set clustering with strict Hard-ID guarding (no false fuzzy merges on phone/account numbers) and Levenshtein token-set fuzzy matching for names ($\ge 0.85$).
- **NetworkX Topology & Centrality**: Node degree centrality, native Louvain community modularity, and boundary BridgeScores.
- **6-Feature ML Hidden-Link Inference**: Link prediction using Common Neighbors, Jaccard, Adamic-Adar, Preferential Attachment, Temporal Decay ($\tau = 3600s$), and Financial Correlation ($\tau = 7200s$).
- **Court-Admissible Precision Gating ($\ge 90\%$)**: Guarantees $\ge 90\%$ precision via cross-validation to prevent false accusations under Section 65B of the Indian Evidence Act.
- **Interactive Visualizers (2D & 3D)**:
  - **Standalone Viewer**: Zero-dependency, runs in any browser (`frontend/standalone_viewer/index.html`).
  - **React Components**: Production-grade Three.js 3D Force Graph and Next.js Graph Page (`frontend/react_components/`).

---

## 📁 Package Structure

```
graph_engine/
├── core/
│   ├── canonicalizer.py         # Union-Find, fuzzy Levenshtein >= 0.85, hard ID isolation
│   ├── builder.py               # NetworkX graph construction, Louvain communities, bridge scores
│   ├── hidden_link_engine.py    # 6 features, Logistic Regression combiner, precision gating >= 90%
│   ├── extractors.py            # Deterministic regex for Indian cyber IDs (PHONE, UPI, etc.)
│   └── serializer.py            # Graph JSON serializer for frontend
├── frontend/
│   ├── standalone_viewer/       # Browser-ready zero-dependency interactive Graph UI
│   │   ├── index.html           # Standalone Cyber Investigation 2D Force Graph Viewer
│   │   ├── app.js               # Physics, search, threshold slider, 2-hop neighborhood
│   │   └── style.css            # Dark-mode styling, glowing neon edges, forensic drawer
│   └── react_components/       # Modular Next.js / React components (graph only)
│       ├── Graph3DCanvas.tsx    # Three.js 3D Force Graph WebGL component
│       ├── GraphPage.tsx        # React / Next.js Case Graph dashboard view
│       └── threatGraphService.ts# Graph API service, types, and schema contracts
├── sample_data/
│   ├── case_mule_syndicate.json # Realistic Indian cyber fraud case evidence events
│   ├── sample_graph.json        # Serialized graph nodes, edges, and hidden links
│   └── sample_graph_visualization.html # Generated interactive graph
├── models/
│   └── hidden_link_model.pkl    # Pre-trained ML weights for link prediction
├── tests/
│   └── test_graph_engine.py     # Comprehensive unit test suite (8 tests)
├── trainer.py                   # Generates training graphs & trains hidden_link_model.pkl
├── demo.py                      # One-command executable demonstration
├── cli.py                       # Command-line interface tool
├── visualizer.py                # Standalone HTML exporter
├── requirements.txt             # Python dependencies
├── HOW_IT_WORKS.md              # Deep-dive architectural and mathematical guide
└── README.md                    # Quickstart and reference (this file)
```

---

## 🚀 Quickstart

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

*(Requires `networkx`, `rapidfuzz`, `scikit-learn`, and `numpy`)*

### 2. Run the End-to-End Demo

```bash
python3 demo.py
```
This will:
1. Load realistic cyber fraud evidence (`sample_data/case_mule_syndicate.json`).
2. Deterministically extract and canonicalize entities.
3. Construct the NetworkX co-occurrence graph.
4. Detect communities and calculate degree centrality & bridge scores.
5. Predict hidden links using the trained model.
6. Generate court-admissible Section 65B explainability reports.
7. Export `sample_data/sample_graph.json` and `sample_data/sample_graph_visualization.html`.

### 3. Open the Standalone Web Visualizer

Open the visualizer directly in any web browser:
```bash
open frontend/standalone_viewer/index.html
# or
open sample_data/sample_graph_visualization.html
```

---

## 💻 CLI Usage

```bash
# Run the demo
python3 cli.py demo

# Train the Hidden Link Model on 40 synthetic case graphs
python3 cli.py train --cases 40 --output models/hidden_link_model.pkl

# Process a case file and output an interactive HTML visualization
python3 cli.py build --input sample_data/case_mule_syndicate.json --output-html my_case.html
```

---

## 🧪 Running Unit Tests

```bash
python3 -m unittest tests/test_graph_engine.py
```

---

## 📚 Technical Documentation

For a comprehensive explanation of the mathematical formulations, Louvain modularity, 6-feature calculations, and precision-gating rationale, read [HOW_IT_WORKS.md](HOW_IT_WORKS.md).
