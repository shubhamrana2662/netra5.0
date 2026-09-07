import type { StoryChapter } from './storyTypes';

export const STORY_CHAPTERS: readonly StoryChapter[] = [
  {
    id: 'problem',
    index: 1,
    label: '01 · THE PROBLEM',
    name: 'ISOLATED FRAGMENTS',
    start: 0.00,
    end: 0.16,
  },
  {
    id: 'correlation',
    index: 2,
    label: '02 · CORRELATION',
    name: 'CONNECTIONS FORM',
    start: 0.16,
    end: 0.35,
  },
  {
    id: 'graph',
    index: 3,
    label: '03 · THE GRAPH',
    name: 'INTELLIGENCE EMERGES',
    start: 0.35,
    end: 0.54,
  },
  {
    id: 'evidence',
    index: 4,
    label: '04 · EVIDENCE TRAIL',
    name: 'FOLLOW THE EVIDENCE',
    start: 0.54,
    end: 0.72,
  },
  {
    id: 'patterns',
    index: 5,
    label: '05 · HIDDEN PATTERNS',
    name: 'REDUCE & REVEAL',
    start: 0.72,
    end: 0.88,
  },
  {
    id: 'resolution',
    index: 6,
    label: '06 · INTELLIGENCE',
    name: 'ACTIONABLE INSIGHT',
    start: 0.88,
    end: 1.00,
  },
] as const;

export const DEBUG_CHECKPOINTS = [
  0.00,
  0.08,
  0.16,
  0.25,
  0.35,
  0.45,
  0.54,
  0.62,
  0.72,
  0.80,
  0.84,
  0.88,
  0.94,
  1.00,
] as const;
