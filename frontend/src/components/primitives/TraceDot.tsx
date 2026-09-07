import type { TraceState } from "../../state/TraceStore";
import s from "./primitives.module.css";

export function TraceDot({ state }: { state: TraceState }) {
  return <i className={`${s.mk} ${s[`mk${state}`]}`} />;
}
