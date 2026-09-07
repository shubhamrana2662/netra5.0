import { mulberry32 } from "../lib/random";
import type { Evidence, EvidenceKind } from "./types";

export type { Evidence };
export const KIND_LABEL: Record<EvidenceKind, string> = {
  DOC: "Document", IMAGE: "Image", DATA: "Data", COMMS: "Comms",
};

const CANONICAL: Evidence[] = [
  { id: "evd-cdr-18", label: "CDR Record 18", kind: "COMMS", meta: "09:42:13 · 14s", status: "VERIFIED", sha256: "a4f912e84c987b12d5e6f3a09c812b74e6f9a0c1d2e3f4b5a6c7d8e9f0a1b2c3", notes: "Anchor communication originating from suspect Device A83F-29." },
  { id: "evd-txn-45000", label: "Transaction 042", kind: "DATA", meta: "₹45,000 · 09:56:13", status: "VERIFIED", sha256: "b5e812d93c876a01e4f5a2b98d701a63d5e8f9b0c1d2e3a4b5c6d7e8f9a0b1c2", notes: "Unauthorized IMPS outbound transfer to Account ••4821 fourteen minutes after anchor." },
  { id: "evd-dev-meta-29", label: "Device Metadata 29", kind: "DATA", meta: "Device A83F-29 · tower 4471", status: "ANALYZED", sha256: "c6f923e04d987b12f5a6b3c09e812b74e6f9a0c1d2e3f4b5a6c7d8e9f0a1b2c4", notes: "Azimuth radio telemetry and IMEI mapping for target hardware." },
  { id: "evd-bank-stmt", label: "Bank Statement ••4821", kind: "DOC", meta: "PDF · Q2 2026", status: "VERIFIED", sha256: "e7a034f15e098c23a6b7c4d10f923c85f7a0b1d2e3f4a5b6c7d8e9f0a1b2c3d5", notes: "Official signed bank ledger from depository institution." },
];

const GENERATED_VERIFIED = new Set(["evd-cdr-04"]);
const p2 = (n: number) => String(n).padStart(2, "0");
const p3 = (n: number) => String(n).padStart(3, "0");
const hhmmss = (r: () => number) =>
  `${p2(Math.floor(r() * 24))}:${p2(Math.floor(r() * 60))}:${p2(Math.floor(r() * 60))}`;
const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

function generate(): Evidence[] {
  const rnd = mulberry32(0x0e42);
  const out: Evidence[] = [];
  const status = (id: string) =>
    GENERATED_VERIFIED.has(id) ? "VERIFIED" : rnd() < 0.15 ? "UNVERIFIED" : "ANALYZED";

  for (let n = 1; n <= 31; n++) {                    // 30 CDR records (18 is canonical)
    if (n === 18) continue;
    const id = `evd-cdr-${p2(n)}`;
    out.push({ id, label: `CDR Record ${p2(n)}`, kind: "COMMS",
      meta: `${hhmmss(rnd)} · ${5 + Math.floor(rnd() * 40)}s`, status: status(id),
      sha256: `7f8b9a${n}c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1` });
  }
  for (let n = 1; n <= 38; n++) {                    // 38 transactions
    const id = `evd-txn-${p3(n)}`;
    out.push({ id, label: `Transaction ${p3(n)}`, kind: "DATA",
      meta: `${inr(2000 + Math.floor(rnd() * 88000))} · ${hhmmss(rnd)}`, status: status(id),
      sha256: `8a9b0c${n}d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef` });
  }
  for (let n = 1; n <= 11; n++) {                    // 11 device metadata
    out.push({ id: `evd-dev-${p2(n)}`, label: `Device Metadata ${p2(n)}`, kind: "DATA",
      meta: `Device ${Math.floor(rnd() * 0xffff).toString(16).toUpperCase().padStart(4, "0")} · tower ${1000 + Math.floor(rnd() * 9000)}`,
      status: "ANALYZED",
      sha256: `9b0c1d${n}e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef01` });
  }
  const months = ["Apr", "May", "Jun", "Jul", "Aug"];
  for (let n = 1; n <= 12; n++) {                    // 12 statements
    out.push({ id: `evd-stmt-${p2(n)}`, label: `Bank Statement ••${1000 + Math.floor(rnd() * 9000)}`, kind: "DOC",
      meta: `PDF · ${months[Math.floor(rnd() * months.length)]} 2026`, status: status(`evd-stmt-${p2(n)}`),
      sha256: `0c1d2e${n}f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef012` });
  }
  for (let n = 1; n <= 11; n++) {                    // 11 annexures
    out.push({ id: `evd-annx-${p2(n)}`, label: `Annexure C-${p2(n)}`, kind: "DOC",
      meta: `Scanned · ${2 + Math.floor(rnd() * 12)} pages`, status: "ANALYZED",
      sha256: `1d2e3f${n}a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef0123` });
  }
  for (let n = 1; n <= 10; n++) {                    // 10 CCTV frames
    const id = `evd-cctv-${p2(n)}`;
    out.push({ id, label: `CCTV Frame ${p2(n)}`, kind: "IMAGE",
      meta: `28.6139° N · ${hhmmss(rnd)}`, status: status(id),
      imageUrl: `https://picsum.photos/seed/cd-cctv-${n}/640/480.jpg`,
      sha256: `2e3f4a${n}b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef01234` });
  }
  for (let n = 1; n <= 8; n++) {                     // 8 scans
    out.push({ id: `evd-scan-${p2(n)}`, label: `Scanned Document ${p2(n)}`, kind: "IMAGE",
      meta: `JPEG · ${1200 + Math.floor(rnd() * 5) * 300} dpi`, status: "ANALYZED",
      sha256: `3f4a5b${n}c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f123456789abcdef012345` });
  }
  return out;
}
/* 30 + 38 + 11 + 12 + 11 + 10 + 8 = 120 generated + 4 canonical = 124 */

const USER_KEY = "cd-evidence-user";
let userEvidence: Evidence[] = [];
try {
  if (typeof window !== "undefined") {
    userEvidence = (JSON.parse(sessionStorage.getItem(USER_KEY) ?? "[]") as Evidence[])
      .map(e => e.status === "PROCESSING" ? { ...e, status: "ANALYZED" as const, meta: "Analyzed · session restored" } : e);
  }
} catch { /* storage unavailable */ }

export function persistUserEvidence(items: Evidence[]): void {
  try {
    if (typeof window !== "undefined") {
      sessionStorage.setItem(USER_KEY, JSON.stringify(items.filter(i => i.user)));
    }
  } catch { /* ignore */ }
}

const generated = generate();
export const evidenceArchive: Evidence[] = [...userEvidence, ...CANONICAL, ...generated];

export const evidenceForCase = (caseId: string): Evidence[] =>
  caseId === "CYB-2026-042" ? evidenceArchive : [];

const KINDS: EvidenceKind[] = ["DOC", "IMAGE", "DATA", "COMMS"];
export function kindCounts(items: Evidence[]) {
  return [
    { kind: "ALL" as const, label: "All", count: items.length },
    ...KINDS.map(k => ({ kind: k, label: KIND_LABEL[k], count: items.filter(i => i.kind === k).length })),
  ];
}
