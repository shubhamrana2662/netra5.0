export interface ChapterContent {
  id: string;
  chapterNumber: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  description: string;
  annotation?: string;
  chips?: string[];
  steps?: { step: string; name: string; detail: string }[];
  discovery?: {
    visibleTitle: string;
    visibleDetail: string;
    hiddenTitle: string;
    hiddenDetail: string;
  };
}

export const IDENTITY_ANCHOR = {
  brand: 'CYBERDRISHTI',
  tagline: 'An intelligence workspace for connecting fragmented cyber evidence.',
};

export const STORY_CONTENT: Record<string, ChapterContent> = {
  problem: {
    id: 'problem',
    chapterNumber: '01',
    eyebrow: '01 · THE PROBLEM',
    title: "Investigations don't begin with answers.",
    subtitle: 'They begin with fragments.',
    description: 'A phone number. A device. A transaction. An IP address. Individually, they float in isolation across digital boundaries.',
    annotation: 'ISOLATED SIGNALS · CONTEXT INCOMPLETE',
    chips: ['PHONE', 'DEVICE', 'ACCOUNT', 'IP'],
  },
  correlation: {
    id: 'correlation',
    chapterNumber: '02',
    eyebrow: '02 · CORRELATION',
    title: 'The signal is not in the data.',
    subtitle: "It's in the relationships between it.",
    description: 'CyberDrishti correlates identities, devices, transactions and infrastructure to expose connections that isolated records cannot reveal.',
    annotation: 'CORRELATION STATUS · RELATIONSHIPS EMERGING',
  },
  graph: {
    id: 'graph',
    chapterNumber: '03',
    eyebrow: '03 · THE GRAPH',
    title: 'See the investigation as one connected system.',
    subtitle: 'Every entity becomes part of a larger intelligence network.',
    description: 'Connected entities form structured groups that reveal operational hierarchies, financial pathways, and shared infrastructure.',
    annotation: 'TOPOLOGY · MULTI-CLUSTER NETWORK',
    chips: ['IDENTITIES', 'DEVICES', 'FINANCIAL FLOWS', 'DIGITAL INFRASTRUCTURE'],
  },
  evidence: {
    id: 'evidence',
    chapterNumber: '04',
    eyebrow: '04 · EVIDENCE TRAIL',
    title: 'Every connection leads somewhere.',
    subtitle: 'Move from entity to defensible finding.',
    description: 'Trace signals step by step: Entity → Relationship → Evidence → Finding. Reconstruct how seemingly unrelated signals form an unbroken evidentiary trail.',
    annotation: 'TRAIL DISCOVERY · DEFUSED SUSPECT CHAIN',
    steps: [
      { step: '01', name: 'ENTITY', detail: 'Initial Signal Ping' },
      { step: '02', name: 'RELATIONSHIP', detail: 'Hardware Binding' },
      { step: '03', name: 'EVIDENCE', detail: 'Mule Account Flow' },
      { step: '04', name: 'FINDING', detail: 'Defensible Finding' },
    ],
  },
  patterns: {
    id: 'patterns',
    chapterNumber: '05',
    eyebrow: '05 · HIDDEN PATTERNS',
    title: 'The most important connections are rarely obvious.',
    subtitle: 'Visible connections reveal hidden patterns.',
    description: 'Background noise dims away. CyberDrishti isolates critical bridge brokers and infers hidden connections across complex syndicates.',
    annotation: 'ANOMALY DETECTION · BRIDGE IDENTIFIED',
    discovery: {
      visibleTitle: 'VISIBLE RECORDS',
      visibleDetail: 'Scattered transactions & hardware registrations',
      hiddenTitle: 'INFERRED PATTERNS',
      hiddenDetail: 'Bridge broker coordination & behavioral synchronization',
    },
  },
  resolution: {
    id: 'resolution',
    chapterNumber: '06',
    eyebrow: '06 · ACTIONABLE INTELLIGENCE',
    title: 'From fragments to intelligence.',
    subtitle: 'Turn disconnected evidence into an investigation you can understand, explore and act on.',
    description: 'The network is resolved. The investigation is ready to explore.',
    annotation: 'SYS.STATUS: RESOLVED · TOPOLOGY READY',
  },
};
