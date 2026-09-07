import { NavLink } from "react-router-dom";
import { motion } from "framer-motion";
import { Icon, type IconName } from "../icons";
import { EASE_OUT } from "../../lib/motion";
import s from "./nav.module.css";

export const INDICATOR_ID = "rail-indicator";

export const NAV_ITEMS: { to: string; icon: IconName; label: string; kbd: string }[] = [
  { to: "/command", icon: "command", label: "Command Center", kbd: "⌘1" },
  { to: "/investigations", icon: "cases", label: "Investigations", kbd: "⌘2" },
  { to: "/intelligence", icon: "intel", label: "Intelligence", kbd: "⌘3" },
];

export function NavRail() {
  return (
    <aside className={s.rail} aria-label="Primary">
      <NavLink to="/command" className={`${s.rItem} ${s.logo}`} aria-label="CyberDrishti home">
        <Icon name="logo" />
      </NavLink>
      <div className={s.divider} />
      {NAV_ITEMS.map(it => (
        <RailItem key={it.to} {...it} />
      ))}
      <div className={s.spacer} />
      <RailItem to="/settings" icon="settings" label="Settings" kbd="⌘0" />
    </aside>
  );
}

function RailItem({ to, icon, label, kbd }: { to: string; icon: IconName; label: string; kbd: string }) {
  return (
    <NavLink
      to={to}
      aria-label={label}
      className={({ isActive }) => [s.rItem, isActive ? s.active : s.idle].join(" ")}
    >
      {({ isActive }) => (
        <>
          <Icon name={icon} />
          <span className={s.tip}>{label} <kbd>{kbd}</kbd></span>
          {isActive && (
            <motion.span
              layoutId={INDICATOR_ID}
              className={s.indicator}
              transition={{ duration: 0.28, ease: EASE_OUT }}
            />
          )}
        </>
      )}
    </NavLink>
  );
}
