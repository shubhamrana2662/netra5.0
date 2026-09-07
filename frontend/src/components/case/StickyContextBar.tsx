import { useEffect, useState, type RefObject } from "react";
import { PriorityMark } from "../primitives/PriorityMark";
import { DemoBadge } from "../DemoBadge";
import type { Priority } from "../../data/types";
import s from "./case.module.css";

interface Props {
  titleRef: RefObject<HTMLElement | null>;
  text: string;
  count?: string;
  priority: Priority;
  demo?: boolean;
}

export function StickyContextBar({ titleRef, text, count, priority, demo = false }: Props) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const el = titleRef.current;
    if (!el) return;
    const io = new IntersectionObserver(
      ([e]) => setShown(!e.isIntersecting),
      { rootMargin: "-60px 0px 0px 0px", threshold: 0 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [titleRef]);

  const emphasis = priority === "HIGH" || priority === "CRITICAL";
  return (
    <div className={shown ? `${s.scBar} ${s.scShown}` : s.scBar} aria-hidden={!shown}>
      <span className={s.scText}>
        {text}
        {count && <span className={s.scCount}>· {count}</span>}
      </span>
      <span className={s.scRight}>
        {demo && <DemoBadge size="sm" />}
        {emphasis && (
          <>
            <span className={s.dot} />
            <PriorityMark priority={priority} />
          </>
        )}
      </span>
    </div>
  );
}
