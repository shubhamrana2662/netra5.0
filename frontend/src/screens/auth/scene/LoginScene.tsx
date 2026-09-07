/**
 * LoginScene — the full-screen real-time 3D environment behind the login panel.
 *
 * Loaded lazily (the auth form paints first), renders one static frame when the
 * OS asks for reduced motion, and self-governs quality: if the rolling frame
 * rate drops below budget the tier degrades (DPR, particle counts, city
 * density) without remounting anything.
 */
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import { FogExp2 } from "three";
import { CameraRig } from "./CameraRig";
import { Connections } from "./Connections";
import {
  AmbientParticles,
  DigitalCity,
  DigitalTerrain,
  ForegroundDust,
  VolumetricHaze,
} from "./Environment";
import { EvidenceField } from "./Evidence";
import { WorldMessages } from "./Messages";
import {
  BlueSatellites,
  CorrelationPulse,
  CriminalSignal,
  InvestigatorSignal,
  TraceFragments,
} from "./Signals";
import { LOOP, story } from "./story";
import { quality } from "./quality";

/** Advances the one clock everything reads; also the runtime FPS governor. */
function StoryDriver({ reduced }: { reduced: boolean }) {
  const setDpr = useThree((s) => s.setDpr);
  const invalidate = useThree((s) => s.invalidate);
  const governor = useRef({ frames: 0, time: 0 });

  useEffect(() => {
    if (reduced) {
      story.t = 23.4; // calm, connected state — a settled world, no motion
      invalidate();
    }
  }, [reduced, invalidate]);

  useFrame((_, rawDt) => {
    if (reduced) return;
    const dt = Math.min(rawDt, 0.05); // clamp tab-switch jumps
    story.t = (story.t + dt) % LOOP;

    const g = governor.current;
    g.frames++;
    g.time += rawDt;
    if (g.time >= 2.5) {
      const fps = g.frames / g.time;
      if (fps < 40 && quality.canDegrade()) {
        quality.degrade();
        setDpr(quality.dprMax());
      }
      g.frames = 0;
      g.time = 0;
    }
  });

  return null;
}

export default function LoginScene({ reduced }: { reduced: boolean }) {
  return (
    <Canvas
      frameloop={reduced ? "demand" : "always"}
      dpr={[1, quality.dprMax()]}
      camera={{ fov: 55, near: 0.5, far: 320, position: [36, 12, 30] }}
      gl={{
        antialias: quality.antialias(),
        powerPreference: "high-performance",
        stencil: false,
        alpha: false,
      }}
      onCreated={({ gl }) => {
        gl.toneMappingExposure = 1.15;
      }}
      style={{ position: "absolute", inset: 0 }}
    >
      <color attach="background" args={["#05070c"]} />
      <fogExp2 attach="fog" args={["#05070c", 0.0092]} />
      <StoryDriver reduced={reduced} />
      <CameraRig />
      {/* layer 5 — deep environment */}
      <VolumetricHaze />
      <DigitalCity />
      <DigitalTerrain />
      <AmbientParticles />
      {/* layer 2/3 — evidence and its graph */}
      <Connections />
      <EvidenceField />
      {/* layer 4 — the actors */}
      <TraceFragments />
      <CriminalSignal />
      <InvestigatorSignal />
      <CorrelationPulse />
      <BlueSatellites />
      {/* world text */}
      <WorldMessages />
      {/* layer 1 — foreground bokeh */}
      <ForegroundDust />
    </Canvas>
  );
}
