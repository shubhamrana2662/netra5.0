import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon } from "../icons";
import { EASE_OUT } from "../../lib/motion";
import { INDICATOR_ID, NAV_ITEMS } from "./NavRail";
import s from "./nav.module.css";

export function BottomBar() {
  return (
    <nav className={s.bottomBar} aria-label="Primary">
      {NAV_ITEMS.map(it => (
        <BottomItem key={it.to} {...it} />
      ))}
      <BottomItem to="/settings" icon="settings" label="Settings" kbd="⌘0" />
    </nav>
  );
}

function BottomItem({ to, icon, label }: { to: string; icon: Parameters<typeof Icon>[0]["name"]; label: string; kbd: string }) {
  return (
    <NavLink
      to={to}
      aria-label={label}
      className={({ isActive }) => [s.bItem, isActive ? s.active : ""].join(" ")}
    >
      {({ isActive }) => (
        <>
          <Icon name={icon} />
          {isActive && (
            <motion.span
              layoutId={INDICATOR_ID}
              className={s.indicatorH}
              transition={{ duration: 0.28, ease: EASE_OUT }}
            />
          )}
        </>
      )}
    </NavLink>
  );
}
