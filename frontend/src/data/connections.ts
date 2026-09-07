import type { Connection } from "./types";
import { entities } from "./entities";

export const connections: Connection[] = [
  {
    id: "con-01",
    a: "ent-device-a83f",
    b: "ent-account-4821",
    reason: "Synchronized timestamps ±14 min",
    confidence: 94,
    type: "associated_with",
    directed: 0
  },
  {
    id: "con-02",
    a: "ent-person-04",
    b: "ent-device-a83f",
    reason: "Shared device metadata",
    confidence: 94,
    type: "uses_device",
    directed: 1
  },
  {
    id: "con-03",
    a: "ent-account-4821",
    b: "ent-account-72",
    reason: "Funds forwarded within minutes of receipt",
    confidence: 89,
    type: "transacts_to",
    directed: 1
  }
];

(function () {
  const G = entities.filter(e => e.id.startsWith('ent-g-')).map(e => e.id);
  const HUBS = ['ent-device-a83f', 'ent-account-4821', 'ent-person-04'];
  const seen = new Set<string>();
  let n = 0;

  const add = (a: string, b: string) => {
    if (a === b || seen.has(a + '|' + b) || seen.has(b + '|' + a)) return;
    seen.add(a + '|' + b);
    n++;
    connections.push({
      id: 'con-g-' + String(n).padStart(2, '0'),
      a,
      b,
      reason: 'Correlated activity window',
      confidence: 68 + ((n * 7) % 30)
    });
  };

  G.forEach((id, i) => add(id, i < 8 ? HUBS[i % 3] : G[(i * 5 + 3) % G.length]));
  for (let i = 0; i < 4; i++) add(G[i], G[i + 7]);
})();
