/**
 * CyberDrishti login scene — story timeline.
 *
 * A single deterministic clock (story.t, seconds inside [0, LOOP)) drives every
 * element of the 3D background. All motion is expressed as a pure function of
 * that clock and every periodic term completes an integer number of cycles per
 * LOOP, so the loop wraps seamlessly: the disperse phase lands the world back
 * in exactly the scattered state the loop opens with.
 *
 * Narrative:
 *   0.0– 4.5  SCATTERED EVIDENCE      fragmented clues float, red links fail
 *   4.5–10.0  THE CRIMINAL MOVES      red signal flees, new evidence spawns
 *  10.0–16.5  INVESTIGATION LAGS      blue signal hops clue to clue, falls behind
 *  16.5–21.0  CORRELATION FAILURE     candidate links flare and break, density rises
 *  21.0–25.0  CYBERDRISHTI PULSE      intelligence wave connects the graph
 *  25.0–28.5  THE GAP CLOSES          blue accelerates along the network, isolates red
 *  28.5–30.0  DISPERSE                world relaxes back into the scattered state
 */
import { CatmullRomCurve3, Vector3 } from "three";

export const LOOP = 30;

/* ---------------------------------- math ---------------------------------- */

export const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);
export const ramp = (t: number, t0: number, t1: number) => clamp01((t - t0) / (t1 - t0));
export const smooth = (t: number) => t * t * (3 - 2 * t);
export const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);
export const easeInOutSine = (t: number) => -(Math.cos(Math.PI * clamp01(t)) - 1) / 2;
/** Rises 0→1→0 across [t0, t0+dur]. */
export const bell = (t: number, t0: number, dur: number) =>
  Math.sin(Math.PI * clamp01((t - t0) / dur));
/** Smooth periodic fade in/out window, 1 while inside [a,b], soft WIDTH edges. */
export const softWindow = (t: number, a: number, b: number, width = 0.6) => {
  const inEdge = smooth(ramp(t, a - width, a));
  const outEdge = 1 - smooth(ramp(t, b, b + width));
  return Math.max(0, Math.min(inEdge, outEdge));
};
/** Monotone piecewise interpolation through [t, value] keypoints (smoothstep joins). */
function keypointLerp(keys: [number, number][], t: number): number {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    if (t <= keys[i][0]) {
      const [ta, va] = keys[i - 1];
      const [tb, vb] = keys[i];
      return va + (vb - va) * smooth((t - ta) / (tb - ta));
    }
  }
  return keys[keys.length - 1][1];
}

/* ------------------------------ story clock ------------------------------- */

export const story = { t: 1.2 };

/* ------------------------------ evidence set ------------------------------ */

export interface EvidenceNode {
  id: number;
  label: string;
  home: [number, number, number];
  /** seed for bobbing phase / rotation speed */
  seed: number;
  /** tint before correlation (neutral evidence) */
  color: string;
  /** nodes that are noise fade out when the graph resolves */
  noise: boolean;
  /** seconds into the loop when the CyberDrishti pulse activates this node */
  activationAt: number;
}

const PULSE_ORIGIN = new Vector3(0, 3, -14);
const PULSE_START = 21;
const PULSE_SPEED = 13.8; // world units / second during the pulse phase

const NODE_DEFS: Array<Omit<EvidenceNode, "activationAt">> = [
  { id: 0, label: "PHONE METADATA", home: [-14, 6, -18], seed: 0.13, color: "#c9d6ea", noise: false },
  { id: 1, label: "BANK TRANSACTION", home: [2, 10, -12], seed: 0.71, color: "#c9d6ea", noise: false },
  { id: 2, label: "IP ADDRESS", home: [16, 5, -20], seed: 0.41, color: "#c9d6ea", noise: false },
  { id: 3, label: "DEVICE FINGERPRINT", home: [8, -2, -6], seed: 0.88, color: "#c9d6ea", noise: false },
  { id: 4, label: "CCTV REFERENCE", home: [-20, -1, -8], seed: 0.27, color: "#c9d6ea", noise: false },
  { id: 5, label: "LOCATION COORDS", home: [-6, -5, -24], seed: 0.55, color: "#c9d6ea", noise: false },
  { id: 6, label: "UPI TRANSACTION", home: [20, 11, -30], seed: 0.34, color: "#c9d6ea", noise: false },
  { id: 7, label: "SOCIAL ACCOUNT", home: [-24, 10, -26], seed: 0.92, color: "#c9d6ea", noise: false },
  { id: 8, label: "SIM REGISTRATION", home: [24, -3, -12], seed: 0.62, color: "#c9d6ea", noise: false },
  { id: 9, label: "EMAIL HEADER", home: [-10, 13, -30], seed: 0.21, color: "#9aa4b5", noise: true },
  { id: 10, label: "TOWER DUMP", home: [12, 14, -4], seed: 0.77, color: "#9aa4b5", noise: true },
  { id: 11, label: "IMEI TRACE", home: [-18, -6, -14], seed: 0.48, color: "#c9d6ea", noise: false },
  { id: 12, label: "VPN EXIT NODE", home: [4, 1, -28], seed: 0.09, color: "#9aa4b5", noise: true },
  { id: 13, label: "WALLET ADDRESS", home: [-2, 7, -2], seed: 0.66, color: "#c9d6ea", noise: false },
];

export const NODES: EvidenceNode[] = NODE_DEFS.map((n) => {
  const d = new Vector3(...n.home).distanceTo(PULSE_ORIGIN);
  return { ...n, activationAt: PULSE_START + 0.2 + d / PULSE_SPEED };
});

export const nodeHome = (i: number) => new Vector3(...NODES[i].home);

/** Data card content, keyed by node id. Cards are holographic fragments. */
export const CARDS: Record<number, { lines: string[] }> = {
  0: { lines: ["MSISDN  +91 98•• ••• 412", "IMSI     404•• ••7721", "REG      22d ago · PREPAID"] },
  1: { lines: ["NEFT     ₹2,40,000", "BENEF    A/C ••4417", "TIME     02:14:09 IST"] },
  2: { lines: ["ADDR     49.36.••.••", "ASN      •••• · CLOUD EDGE", "GEO      IN / MUMBAI"] },
  3: { lines: ["HASH     a41f••••••••9c2e", "OS       ANDROID 13", "AGENT    OPENCRM/2.1"] },
  4: { lines: ["CAM      CCTV-1147-B", "FRAME    01:58:44", "MATCH    PENDING"] },
  5: { lines: ["LAT      19.07•• N", "LON      72.87•• E", "SRC      GPS / CELL"] },
  6: { lines: ["VPA      name••@upi", "AMT      ₹18,500", "STATUS   SUCCESS"] },
  7: { lines: ["HANDLE   @••••_07", "CREATED  8mo ago", "LINKS    3 CONTACTS"] },
  8: { lines: ["ICCID    8991•• •••• 3025", "CIRCLE   MH / GOA", "STATUS   ACTIVE"] },
};

/* --------------------------------- edges ---------------------------------- */

export interface EdgeDef {
  a: number;
  b: number;
  /** second into the loop when the attempted connection fails (red flash) */
  failAt: number;
}

/** Attempted-but-broken links. One fail event per loop each. */
export const CANDIDATE_EDGES: EdgeDef[] = [
  { a: 0, b: 1, failAt: 2.6 },
  { a: 2, b: 4, failAt: 3.4 },
  { a: 5, b: 11, failAt: 4.2 },
  { a: 1, b: 3, failAt: 6.1 },
  { a: 6, b: 2, failAt: 7.3 },
  { a: 7, b: 9, failAt: 8.2 },
  { a: 8, b: 3, failAt: 9.1 },
  { a: 10, b: 1, failAt: 10.4 },
  { a: 12, b: 2, failAt: 11.3 },
  { a: 9, b: 0, failAt: 12.2 },
  { a: 11, b: 3, failAt: 13.1 },
  { a: 4, b: 0, failAt: 13.9 },
  { a: 5, b: 12, failAt: 14.7 },
  { a: 7, b: 0, failAt: 15.5 },
  { a: 6, b: 10, failAt: 16.3 },
  { a: 1, b: 9, failAt: 17.0 },
  { a: 8, b: 12, failAt: 17.6 },
  { a: 10, b: 3, failAt: 18.2 },
  { a: 2, b: 0, failAt: 18.8 },
  { a: 11, b: 13, failAt: 19.3 },
  { a: 7, b: 4, failAt: 19.8 },
  { a: 9, b: 6, failAt: 20.2 },
];

/** Correlated graph — the relationships CyberDrishti reveals (PULSE phase). */
export const CORRELATED_EDGES: Array<[number, number]> = [
  [4, 11],
  [5, 11],
  [0, 5],
  [0, 13],
  [1, 13],
  [3, 13],
  [2, 13],
  [2, 8],
  [6, 8],
  [1, 3],
  [7, 0],
  [6, 3],
];

/** Seconds into the loop when each correlated edge lights up (pulse wavefront). */
export const CORRELATED_AT: number[] = CORRELATED_EDGES.map(([a, b]) => {
  const mid = new Vector3(...NODES[a].home)
    .add(new Vector3(...NODES[b].home))
    .multiplyScalar(0.5);
  return PULSE_START + 0.35 + mid.distanceTo(PULSE_ORIGIN) / PULSE_SPEED;
});

/* -------------------------------- criminal -------------------------------- */

/** Closed flight loop winding outside the evidence cloud. */
export const CRIMINAL_PATH = new CatmullRomCurve3(
  [
    new Vector3(40, 2, -10),
    new Vector3(30, 6, -42),
    new Vector3(-6, 9, -52),
    new Vector3(-38, 4, -34),
    new Vector3(-46, -2, 4),
    new Vector3(-24, 3, 26),
    new Vector3(14, 6, 24),
    new Vector3(42, 1, 12),
  ],
  true,
  "catmullrom",
  0.6,
);

const CRIMINAL_U0 = 0.66;
const CRIMINAL_S: [number, number][] = [
  [4.5, 0.0],
  [10, 0.095],
  [16.5, 0.235],
  [21, 0.36],
  [25, 0.455],
  [27.2, 0.545],
  [27.9, 0.562],
  [30, 0.562],
];

/** Arc-length position u along the flight loop at loop-time t. */
export function criminalU(t: number): number {
  return (CRIMINAL_U0 + keypointLerp(CRIMINAL_S, t)) % 1;
}

const _cp = new Vector3();
export function criminalPos(t: number, out: Vector3 = _cp): Vector3 {
  return CRIMINAL_PATH.getPointAt(criminalU(t), out);
}

/** Visible envelope of the red signal (fades in as it spawns, out as world disperses). */
export function criminalAlpha(t: number): number {
  return softWindow(t, 4.9, 28.6, 0.7);
}

/* ------------------------------ investigator ------------------------------ */

interface Hop {
  node: number;
  arrive: number;
  dwell: number;
}
/** Blue signal search sequence: reach a clue, scan, stall, move on. */
const HOPS: Hop[] = [
  { node: 4, arrive: 10.0, dwell: 1.6 },
  { node: 11, arrive: 12.4, dwell: 1.4 },
  { node: 5, arrive: 14.9, dwell: 1.6 },
  { node: 0, arrive: 17.3, dwell: 2.7 },
  { node: 2, arrive: 20.3, dwell: 4.7 },
];
const PURSUE_T0 = 25.0;
const PURSUE_T1 = 27.3;

const _ip = new Vector3();
const _from = new Vector3();
const _to = new Vector3();
const _ctl = new Vector3();

/** Investigator signal position at loop-time t. */
export function investigatorPos(t: number, out: Vector3 = _ip): Vector3 {
  if (t < HOPS[0].arrive) return nodeHome(HOPS[0].node);
  for (let i = 0; i < HOPS.length; i++) {
    const h = HOPS[i];
    const depart = h.arrive + h.dwell;
    if (t < depart || i === HOPS.length - 1) {
      if (t < h.arrive && i > 0) {
        // traveling from previous node
        const prev = HOPS[i - 1];
        return lerpNodes(nodeHome(prev.node), nodeHome(h.node), easeInOutSine((t - (prev.arrive + prev.dwell)) / (h.arrive - (prev.arrive + prev.dwell))), out);
      }
      // dwelling at this node (scan bob)
      const p = nodeHome(h.node);
      out.copy(p);
      out.y += Math.sin((t - h.arrive) * 2.1) * 0.35;
      out.x += Math.sin((t - h.arrive) * 1.3 + h.node) * 0.3;
      return out;
    }
  }
  return nodeHome(HOPS[HOPS.length - 1].node);
}

function lerpNodes(a: Vector3, b: Vector3, k: number, out: Vector3): Vector3 {
  return out.copy(a).lerp(b, k);
}

/**
 * 0 = searching (hops + stalls), 1 = full pursuit along the correlated network.
 * The transition is the moment correlation succeeds and the gap starts closing.
 */
export const investigatorPursuit = (t: number) => smooth(ramp(t, PURSUE_T0 - 0.4, PURSUE_T0 + 0.6));

export function investigatorAlpha(t: number): number {
  return softWindow(t, 10.0, 28.9, 0.7);
}

/** Pursuit path is recomputed each frame toward the (stopped) criminal. */
export function investigatorPursuePos(t: number, out: Vector3): Vector3 {
  const from = nodeHome(HOPS[HOPS.length - 1].node);
  const target = criminalPos(Math.min(t, 27.9), _to);
  const k = easeInOutSine(ramp(t, PURSUE_T0, PURSUE_T1));
  _from.copy(from);
  _ctl.copy(_from).add(target).multiplyScalar(0.5);
  _ctl.y += 7;
  // quadratic bezier
  const a = 1 - k;
  out.set(
    a * a * _from.x + 2 * a * k * _ctl.x + k * k * target.x,
    a * a * _from.y + 2 * a * k * _ctl.y + k * k * target.y,
    a * a * _from.z + 2 * a * k * _ctl.z + k * k * target.z,
  );
  return out;
}

/** Scan rings emitted at each dwell (t offsets into the loop). */
export const SCAN_RINGS: Array<{ at: number; node: number }> = HOPS.flatMap((h, i) => {
  const rings = [{ at: h.arrive + 0.25, node: h.node }];
  // frantic re-scans during the correlation-failure peak at the last two stops
  if (i === 3) rings.push({ at: h.arrive + 1.2, node: h.node }, { at: h.arrive + 2.0, node: h.node });
  if (i === 4) rings.push({ at: h.arrive + 1.4, node: h.node }, { at: h.arrive + 2.4, node: h.node });
  return rings;
});

/* ------------------------------ CD pulse wave ----------------------------- */

/** Radius of the intelligence wavefront at loop-time t (0 before the pulse). */
export function pulseRadius(t: number): number {
  if (t < PULSE_START) return 0;
  const dt = t >= 28.5 ? t - LOOP - PULSE_START : t - PULSE_START; // never re-fires at wrap
  return Math.max(0, Math.min(dt, 3.4) * PULSE_SPEED * easeOutCubic(clamp01(dt / 3.4)) * 1.35);
}

/**
 * Global fade applied to every "resolved" element (node colors, correlated
 * edges, dimmed noise) so the connected graph relaxes back to the scattered
 * state during DISPERSE — the wrap then lands exactly on the opening frame.
 */
export function correlationFade(t: number): number {
  return 1 - smooth(ramp(t, 28.55, 29.55));
}

/** Node activation envelope: flash on at `at`, release during disperse. */
export function nodeActivation(t: number, at: number): number {
  return easeOutCubic(ramp(t, at, at + 0.9)) * correlationFade(t);
}

/** Satellites close in on the isolated criminal during THE GAP CLOSES. */
export const SATELLITES = 5;
export function satelliteK(t: number, i: number): number {
  return easeOutCubic(ramp(t, 26.2 + i * 0.18, 27.6 + i * 0.18));
}

/* ------------------------------- messaging -------------------------------- */

export interface WorldMessage {
  text: string;
  at: number;
  hold: number;
  color: string;
  pos: [number, number, number];
}

export const MESSAGES: WorldMessage[] = [
  { text: "UNKNOWN ACTOR DETECTED", at: 5.4, hold: 2.6, color: "#ff6b6b", pos: [18, 9, -2] },
  { text: "CORRELATION DELAY · 08m 42s", at: 11.6, hold: 3.0, color: "#8fb8ff", pos: [-22, 6, -16] },
  { text: "UNRESOLVED CONNECTION", at: 17.2, hold: 2.2, color: "#ff6b6b", pos: [24, 7, -22] },
  { text: "MULTIPLE DATA SILOS DETECTED", at: 18.6, hold: 2.4, color: "#c9d6ea", pos: [-14, 16, -24] },
  { text: "PATTERN DISCOVERED", at: 21.9, hold: 2.8, color: "#7fd4ff", pos: [0, 17, -18] },
  { text: "CONNECTION ESTABLISHED", at: 26.4, hold: 2.6, color: "#7fd4ff", pos: [-30, 8, -18] },
  { text: "INVESTIGATION ACCELERATED", at: 27.6, hold: 2.4, color: "#8fb8ff", pos: [22, -6, -26] },
];

/* --------------------------------- camera --------------------------------- */

const CAMERA_PATH = new CatmullRomCurve3(
  [
    new Vector3(36, 12, 30),
    new Vector3(30, 10, -38),
    new Vector3(-2, 14, -52),
    new Vector3(-34, 8, -40),
    new Vector3(-44, 6, -6),
    new Vector3(-30, 12, 26),
    new Vector3(6, 16, 38),
    new Vector3(38, 14, 22),
  ],
  true,
  "catmullrom",
  0.5,
);

const _cam = new Vector3();
export function cameraPos(t: number, out: Vector3 = _cam): Vector3 {
  return CAMERA_PATH.getPointAt((t / LOOP) % 1, out);
}

/**
 * Look-at weight toward the fleeing criminal: the camera tracks the chase in
 * the middle acts, releases to the full graph for the CyberDrishti moment.
 */
export function cameraChaseWeight(t: number): number {
  const on = smooth(ramp(t, 5.5, 8.5));
  const off = smooth(ramp(t, 23.5, 26.5));
  return on * (1 - off);
}

/** Extra tension: the camera inches closer to the failing graph at the peak. */
export function cameraTension(t: number): number {
  return bell(t, 18.5, 6);
}

export const LOOK_CENTER = PULSE_ORIGIN;
