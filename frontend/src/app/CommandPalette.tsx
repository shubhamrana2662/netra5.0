import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Icon, type IconName } from "../components/icons";
import { useLiveStore } from "../state/useLiveStore";
import { EASE_OUT } from "../lib/motion";
import s from "./palette.module.css";

interface Item {
  id: string;
  group: string;
  label: string;
  hint?: string;
  icon?: IconName;
  run: () => void;
}

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const navigate = useNavigate();
  const { cases: liveCases } = useLiveStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);

  const items = useMemo<Item[]>(
    () => [
      {
        id: "act-new-case",
        group: "Actions",
        label: "New investigation",
        icon: "plus",
        run: () => navigate("/investigations"),
      },
      ...(liveCases[0]
        ? [{
            id: "act-report",
            group: "Actions",
            label: "Generate Section 63 BSA certificate",
            icon: "download" as IconName,
            run: () => navigate(`/investigations/${liveCases[0].id}/report`),
          }]
        : []),
      ...([
        { to: "/command", icon: "command", label: "Command Center", hint: "⌘1" },
        { to: "/investigations", icon: "cases", label: "Investigations", hint: "⌘2" },
        { to: "/intelligence", icon: "intel", label: "Intelligence", hint: "⌘3" },
        { to: "/settings", icon: "settings", label: "Settings", hint: "⌘0" },
      ] as const).map(i => ({
        id: `nav-${i.to}`,
        group: "Navigation",
        icon: i.icon as IconName,
        label: i.label,
        hint: i.hint,
        run: () => navigate(i.to),
      })),
      ...liveCases.map(c => ({
        id: `case-${c.id}`,
        group: "Investigations",
        label: c.name,
        hint: c.id,
        run: () => navigate(`/investigations/${c.id}/overview`),
      })),
      ...liveCases.map(c => ({
        id: `evd-${c.id}`,
        group: "Quick Evidence Jump",
        label: `Evidence · ${c.name}`,
        hint: c.id,
        run: () => navigate(`/investigations/${c.id}/evidence`),
      })),
    ],
    [navigate, liveCases],
  );

  const filtered = items.filter(i =>
    i.label.toLowerCase().includes(q.trim().toLowerCase()) ||
    (i.hint && i.hint.toLowerCase().includes(q.trim().toLowerCase())),
  );
  const clamped = Math.min(idx, Math.max(0, filtered.length - 1));
  const activeItemId = filtered[clamped]?.id;

  useEffect(() => {
    if (open) {
      setQ("");
      setIdx(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    listRef.current?.querySelector("[data-sel]")?.scrollIntoView({ block: "nearest" });
  }, [clamped]);

  // Focus trap inside the modal dialog
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "Tab") {
        e.preventDefault(); // Keep focus trapped on input
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const choose = (i: number) => {
    const it = filtered[i];
    onClose();
    if (it) setTimeout(it.run, 0);
  };

  return (
    <AnimatePresence>
      {open && (
        <div className={s.palette} role="presentation">
          <motion.div
            className={s.overlay}
            initial={{ opacity: 0 }} animate={{ opacity: 1 }}
            exit={{ opacity: 0 }} transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.div
            ref={panelRef}
            role="dialog"
            aria-modal="true"
            aria-label="Command palette"
            className={s.panel}
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6, transition: { duration: 0.16 } }}
            transition={{ duration: 0.2, ease: EASE_OUT }}
          >
            <div className={s.inputRow}>
              <Icon name="search" size={16} />
              <input
                ref={inputRef}
                value={q}
                role="combobox"
                aria-expanded={open}
                aria-autocomplete="list"
                aria-controls="palette-options"
                aria-activedescendant={activeItemId}
                placeholder="Search intelligence, commands, cases…"
                onChange={e => { setQ(e.target.value); setIdx(0); }}
                onKeyDown={e => {
                  if (e.key === "ArrowDown" && filtered.length) {
                    e.preventDefault();
                    setIdx(i => (clamped + 1) % filtered.length);
                  } else if (e.key === "ArrowUp" && filtered.length) {
                    e.preventDefault();
                    setIdx(i => (clamped - 1 + filtered.length) % filtered.length);
                  } else if (e.key === "Enter") {
                    e.preventDefault();
                    choose(clamped);
                  }
                }}
              />
            </div>
            <ul className={s.list} ref={listRef} id="palette-options" role="listbox" aria-label="Suggestions">
              {filtered.length === 0 && <li className={s.group} role="status">No matching commands</li>}
              {filtered.map((it, i) => {
                const showGroup = i === 0 || filtered[i - 1].group !== it.group;
                const isSelected = i === clamped;
                return (
                  <Fragment key={it.id}>
                    {showGroup && <li className={s.group} role="presentation">{it.group}</li>}
                    <li
                      id={it.id}
                      role="option"
                      aria-selected={isSelected}
                      className={s.item}
                      data-sel={isSelected ? "" : undefined}
                      onMouseEnter={() => setIdx(i)}
                      onClick={() => choose(i)}
                    >
                      <Icon name={it.icon ?? "arrow"} size={16} />
                      <span>{it.label}</span>
                      {it.hint && <span className={s.hint}>{it.hint}</span>}
                    </li>
                  </Fragment>
                );
              })}
            </ul>
            <div className={s.foot}>
              <span>↑↓ NAVIGATE</span><span>↵ EXECUTE</span><span>ESC CLOSE</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
