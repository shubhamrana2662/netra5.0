import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Icon, type IconName } from "../icons";
import s from "./primitives.module.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  icon?: IconName;
  children: ReactNode;
}

export function Button({ variant = "secondary", icon, children, className, ...rest }: Props) {
  return (
    <button className={[s.btn, s[variant], className].filter(Boolean).join(" ")} {...rest}>
      {children}
      {icon && <Icon name={icon} size={14} />}
    </button>
  );
}
