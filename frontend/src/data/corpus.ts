import { cases } from "./cases";
import { entities } from "./entities";
import { evidenceArchive, evidenceForCase } from "./evidence";
import { events } from "./events";
import { connections } from "./connections";
import { findings } from "./findings";
import { landingThread } from "./thread";

export { cases, entities, events, connections, findings, landingThread, evidenceForCase };

export const evidence = evidenceArchive;
export const caseById = new Map(cases.map(c => [c.id, c]));
export const entityById = new Map(entities.map(e => [e.id, e]));
export const evidenceById = new Map(evidenceArchive.map(e => [e.id, e]));

export const evidenceLabel = (id: string): string => evidenceById.get(id)?.label ?? id;

export const eventsForCase = (_caseId: string): typeof events => events;
export const connectionsForCase = (_caseId: string): typeof connections => connections;
export const findingsForCase = (_caseId: string): typeof findings => findings;
