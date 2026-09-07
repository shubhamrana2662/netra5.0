import { STORY_CHAPTERS } from './storyConfig';
import type { StoryChapter } from './storyTypes';

export function clamp(value: number, min = 0, max = 1): number {
  return Math.min(max, Math.max(min, value));
}

export function lerp(from: number, to: number, t: number): number {
  return from + (to - from) * t;
}

export function inverseLerp(value: number, start: number, end: number): number {
  if (end === start) return 0;
  return clamp((value - start) / (end - start));
}

export function mapRange(
  value: number,
  inStart: number,
  inEnd: number,
  outStart = 0,
  outEnd = 1
): number {
  const t = inverseLerp(value, inStart, inEnd);
  return lerp(outStart, outEnd, t);
}

export function smoothstep(t: number): number {
  const x = clamp(t);
  return x * x * (3 - 2 * x);
}

export function easeInOutCubic(t: number): number {
  const x = clamp(t);
  return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
}

export function easeOutQuad(t: number): number {
  const x = clamp(t);
  return 1 - (1 - x) * (1 - x);
}

export function getChapterProgress(storyProgress: number, chapter: StoryChapter): number {
  return inverseLerp(storyProgress, chapter.start, chapter.end);
}

export function getActiveChapter(storyProgress: number): StoryChapter {
  const p = clamp(storyProgress, 0, 1);
  return (
    STORY_CHAPTERS.find(
      (ch) => p >= ch.start && p < ch.end
    ) ?? STORY_CHAPTERS[STORY_CHAPTERS.length - 1]
  );
}
