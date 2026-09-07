import type { Entity } from "./types";

export const entities: Entity[] = [
  {
    id: "ent-person-04",
    name: "Rajesh Kumar",
    kind: "PERSON",
    meta: "Entity #04 · 18 connections",
    risk: "HIGH",
    mentionCount: 29,
    linkedEvidenceIds: ["evd-cdr-18", "evd-annx-01"],
  },
  {
    id: "ent-device-a83f",
    name: "Device A83F-29",
    kind: "DEVICE",
    meta: "Linked to 4 identities · Jamtara cluster",
    mentionCount: 38,
    linkedEvidenceIds: ["evd-cdr-18", "evd-dev-meta-29", "evd-cdr-04"],
  },
  {
    id: "ent-account-4821",
    name: "Account ••4821",
    kind: "ACCOUNT",
    meta: "₹2.4M traced · Axis Bank Mumbai",
    risk: "HIGH",
    mentionCount: 32,
    linkedEvidenceIds: ["evd-txn-45000", "evd-bank-stmt"],
  },
  {
    id: "ent-account-72",
    name: "Account #72",
    kind: "ACCOUNT",
    meta: "Newly linked via UPI layer · HDFC",
    risk: "MEDIUM",
    mentionCount: 17,
    linkedEvidenceIds: ["evd-txn-012", "evd-bank-stmt"],
  },
];

// Generated entities to complete the 24-node canonical graph
(function () {
  const P = ['Entity #05', 'Entity #06', 'Entity #07', 'Entity #08', 'Entity #09', 'Entity #10', 'Entity #11'];
  const D = ['B41C', 'C9A2', 'D7E1', 'E3F8', 'F0A6'];
  const A = ['3120', '7290', '0774', '5501', '8842', '2210'];
  const O = ['Meridian Trade Services', 'Kestrel Logistics Pvt. Ltd.'];

  P.forEach((n, i) => entities.push({
    id: 'ent-g-p' + (i + 1),
    name: n,
    kind: 'PERSON',
    meta: (2 + (i * 3) % 7) + ' connections',
    risk: i === 2 ? 'HIGH' : undefined,
    mentionCount: 5 + i * 2,
    linkedEvidenceIds: ['evd-cdr-04']
  }));

  D.forEach((d, i) => entities.push({
    id: 'ent-g-d' + (i + 1),
    name: 'Device ' + d + '-' + (10 + i),
    kind: 'DEVICE',
    meta: 'Tower 4' + (100 + i * 7) + ' · ' + (1 + i % 3) + ' identities',
    mentionCount: 8 + i,
    linkedEvidenceIds: ['evd-dev-meta-29']
  }));

  A.forEach((a, i) => entities.push({
    id: 'ent-g-a' + (i + 1),
    name: 'Account ••' + a,
    kind: 'ACCOUNT',
    meta: '₹' + (0.2 + i * 0.35).toFixed(1) + 'M flow',
    mentionCount: 12 + i,
    linkedEvidenceIds: ['evd-txn-45000']
  }));

  O.forEach((o, i) => entities.push({
    id: 'ent-g-o' + (i + 1),
    name: o,
    kind: 'ORG',
    meta: 'Registered 2025 · under review',
    mentionCount: 6,
    linkedEvidenceIds: ['evd-bank-stmt']
  }));
})();
