import { type RefObject, useEffect, useRef, useState } from 'react';
import { clamp } from './storyUtils';

/**
 * Deterministic hook that converts physical container scroll position
 * into a single normalized progress value: storyProgress ∈ [0.0, 1.0].
 *
 * Uses requestAnimationFrame throttling to guarantee high performance without
 * frame drops or unthrottled React state cascades.
 */
export function useStoryProgress(storyRef: RefObject<HTMLElement>): number {
  const [progress, setProgress] = useState(0);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    const updateProgress = () => {
      frameRef.current = null;
      const element = storyRef.current;
      if (!element) return;

      const rect = element.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      const scrollDistance = element.offsetHeight - viewportHeight;

      if (scrollDistance <= 0) {
        setProgress(0);
        return;
      }

      // Normalized storyProgress:
      // When rect.top === 0 -> 0.0 (story starts)
      // When rect.top === -scrollDistance -> 1.0 (story finishes)
      const nextProgress = clamp(-rect.top / scrollDistance, 0, 1);
      setProgress(nextProgress);
    };

    const handleScroll = () => {
      if (frameRef.current !== null) return;
      frameRef.current = requestAnimationFrame(updateProgress);
    };

    updateProgress();

    window.addEventListener('scroll', handleScroll, { passive: true });
    window.addEventListener('resize', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
      window.removeEventListener('resize', handleScroll);
      if (frameRef.current !== null) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, [storyRef]);

  return progress;
}
