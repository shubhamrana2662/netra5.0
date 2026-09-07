import type { Case } from "./types";
import { ANCHOR_TIMESTAMP } from "./thread";

/**
 * The single canonical demonstration case.
 *
 * This is SYNTHETIC data — it exists only to demonstrate the platform. It is
 * tagged `SYNTHETIC_DEMO` so the UI can badge it and so it can never be
 * mistaken for a real investigation. Real cases come exclusively from the
 * backend via LiveStore; nothing here is ever substituted for missing live
 * data.
 */
export const DEMO_CASE: Case = {
  id: "CYB-2026-042",
  name: "Operation Shadowlink",
  domain: "Financial fraud",
  entities: 24, evidence: 124, leads: 8,
  priority: "HIGH", status: "ACTIVE", updated: "18m ago",
  brief: `A coordinated financial fraud network involving multiple accounts, identities and communication channels. The sequence anchors on a ${ANCHOR_TIMESTAMP} communication from Device A83F; a ₹45,000 transfer through Account ••4821 follows fourteen minutes later.`,
  latest: "A previously unknown financial connection was identified between Entity #04 and Account #72.",
  source_type: "SYNTHETIC_DEMO",
};

/** @deprecated Use {@link DEMO_CASE}. Retained as an array for legacy imports. */
export const cases: Case[] = [DEMO_CASE];
