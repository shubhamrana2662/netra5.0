import type { CSSProperties, ReactNode } from "react";
import { motion, type Variants } from "framer-motion";
import { EASE_OUT, EASE_SOFT, DUR, STAGGER } from "../lib/motion";

/** Global Page Route Transition */
export const page: Variants = {
  initial: {
    opacity: 0,
    y: 6,
    filter: "blur(4px)"
  },
  animate: {
    opacity: 1,
    y: 0,
    filter: "blur(0px)",
    transition: {
      duration: DUR.page,
      ease: EASE_OUT
    }
  },
  exit: {
    opacity: 0,
    y: -4,
    filter: "blur(2px)",
    transition: {
      duration: DUR.micro,
      ease: EASE_SOFT
    }
  }
};

/** Individual Editorial Block Transition */
export const block: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.interface, ease: EASE_OUT }
  },
  exit: { opacity: 0, transition: { duration: DUR.micro } }
};

/** Investigation Workspace Dimension / Tab Transition */
export const tabSwap: Variants = {
  initial: {
    opacity: 0,
    y: 6,
    scale: 0.996,
    filter: "blur(3px)"
  },
  animate: {
    opacity: 1,
    y: 0,
    scale: 1,
    filter: "blur(0px)",
    transition: {
      duration: DUR.interface,
      ease: EASE_OUT
    }
  },
  exit: {
    opacity: 0,
    y: -4,
    scale: 0.998,
    filter: "blur(2px)",
    transition: {
      duration: DUR.micro,
      ease: EASE_SOFT
    }
  }
};

/** Orchestrated Dashboard Stagger Container */
export const staggerContainer: Variants = {
  initial: {},
  animate: {
    transition: {
      staggerChildren: 0.045,
      delayChildren: 0.02
    }
  }
};

/** Dashboard Card / Row Reveal */
export const staggerItem: Variants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DUR.interface, ease: EASE_OUT }
  }
};

/** Detail Panel & Drawer Slide Variant */
export const drawerSlide: Variants = {
  initial: { x: "100%", opacity: 0.5 },
  animate: {
    x: 0,
    opacity: 1,
    transition: { duration: DUR.panel, ease: EASE_OUT }
  },
  exit: {
    x: "100%",
    opacity: 0,
    transition: { duration: DUR.interface, ease: EASE_SOFT }
  }
};

export function Block({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <motion.div variants={block} className={className} style={style}>
      {children}
    </motion.div>
  );
}
