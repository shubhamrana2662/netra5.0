/**
 * The story's actors:
 *  - CriminalSignal: red distorted entity fleeing on a closed loop, shedding a
 *    GPU-faded particle trail; new evidence fragments pop along its path
 *  - InvestigatorSignal: blue intelligence signal that hops clue→clue, stalls,
 *    scans (expanding rings), then — once correlated — accelerates straight
 *    along the network and corners the criminal with blue satellites
 *  - CorrelationPulse: the CyberDrishti wavefront expanding from the center
 */
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  Group,
  IcosahedronGeometry,
  Mesh,
  MeshBasicMaterial,
  Points,
  ShaderMaterial,
  SphereGeometry,
  Sprite,
  SpriteMaterial,
  Vector3,
} from "three";
import {
  CRIMINAL_PATH,
  SCAN_RINGS,
  SATELLITES,
  bell,
  clamp01,
  criminalAlpha,
  criminalPos,
  criminalU,
  easeOutCubic,
  investigatorAlpha,
  investigatorPos,
  investigatorPursuit,
  investigatorPursuePos,
  pulseRadius,
  satelliteK,
  softWindow,
  story,
} from "./story";
import { quality } from "./quality";
import { PULSE_FRAG, PULSE_VERT, TRAIL_FRAG, TRAIL_VERT } from "./shaders";
import { glowTexture, ringTexture } from "./textures";

const _pos = new Vector3();
const _sat = new Vector3();
const _dir = new Vector3();

/* ----------------------------- criminal signal ---------------------------- */

const TRAIL_MAX = 240;

export function CriminalSignal() {
  const wall = useRef(0);
  const cursor = useRef(0);
  const lastSpawn = useRef(0);

  const built = useMemo(() => {
    const group = new Group();

    const coreMat = new SpriteMaterial({
      map: glowTexture(),
      color: new Color("#ff4545"),
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      opacity: 0.95,
    });
    const core = new Sprite(coreMat);
    core.scale.setScalar(7);
    group.add(core);

    const shellMat = new MeshBasicMaterial({
      color: new Color("#ff8585"),
      wireframe: true,
      transparent: true,
      opacity: 0.65,
    });
    const shell = new Mesh(new IcosahedronGeometry(1.15, 1), shellMat);
    group.add(shell);

    const innerMat = new SpriteMaterial({
      map: glowTexture(),
      color: new Color("#ffd9d9"),
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      opacity: 0.9,
    });
    const inner = new Sprite(innerMat);
    inner.scale.setScalar(2.2);
    group.add(inner);

    // trail ring buffer (world-space Points object)
    const positions = new Float32Array(TRAIL_MAX * 3);
    const births = new Float32Array(TRAIL_MAX).fill(-1000);
    const lifes = new Float32Array(TRAIL_MAX).fill(2.4);
    const scales = new Float32Array(TRAIL_MAX);
    for (let i = 0; i < TRAIL_MAX; i++) scales[i] = 1.6 + (i % 5) * 0.5;
    const geo = new BufferGeometry();
    geo.setAttribute("position", new BufferAttribute(positions, 3));
    geo.setAttribute("aBirth", new BufferAttribute(births, 1));
    geo.setAttribute("aLife", new BufferAttribute(lifes, 1));
    geo.setAttribute("aScale", new BufferAttribute(scales, 1));
    const trailMat = new ShaderMaterial({
      vertexShader: TRAIL_VERT,
      fragmentShader: TRAIL_FRAG,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      uniforms: {
        uTime: { value: 0 },
        uPixelRatio: { value: 1 },
        uColor: { value: new Color("#ff5c5c") },
      },
    });
    const trail = new Points(geo, trailMat);
    trail.frustumCulled = false;

    return { group, coreMat, shellMat, innerMat, shell, geo, trailMat, trail, births, positions };
  }, []);

  useFrame((_, rawDt) => {
    const dt = Math.min(rawDt, 0.05);
    wall.current += dt;
    const t = story.t;
    const alpha = criminalAlpha(t);
    built.group.visible = alpha > 0.01;
    if (!built.group.visible) {
      // kill the trail while the actor is offstage (loop wrap)
      if (built.births[cursor.current] > -500) {
        for (let i = 0; i < TRAIL_MAX; i++) built.births[i] = -1000;
        (built.geo.attributes.aBirth as BufferAttribute).needsUpdate = true;
      }
      return;
    }

    criminalPos(t, _pos);
    built.group.position.copy(_pos);
    built.shell.rotation.y += dt * 2.2;
    built.shell.rotation.x += dt * 1.1;
    const pulse = 1 + Math.sin(wall.current * 9) * 0.08;
    built.coreMat.opacity = alpha * 0.95 * pulse;
    built.shellMat.opacity = alpha * 0.65;
    built.innerMat.opacity = alpha * 0.9;

    // spawn trail while moving
    const moving = t > 4.9 && t < 27.9;
    built.trailMat.uniforms.uTime.value = wall.current;
    const budget = quality.count("trail");
    if (moving && wall.current - lastSpawn.current > 0.026) {
      lastSpawn.current = wall.current;
      const i = cursor.current % budget;
      built.positions[i * 3] = _pos.x;
      built.positions[i * 3 + 1] = _pos.y;
      built.positions[i * 3 + 2] = _pos.z;
      built.births[i] = wall.current;
      cursor.current++;
      (built.geo.attributes.position as BufferAttribute).needsUpdate = true;
      (built.geo.attributes.aBirth as BufferAttribute).needsUpdate = true;
      built.geo.setDrawRange(0, budget);
    }
  });

  return (
    <group>
      <primitive object={built.group} />
      <primitive object={built.trail} />
    </group>
  );
}

/* --------------------------- investigator signal -------------------------- */

const RING_POOL = 8;
const RING_LIFE = 1.5;

export function InvestigatorSignal() {
  const built = useMemo(() => {
    const group = new Group();

    const coreMat = new SpriteMaterial({
      map: glowTexture(),
      color: new Color("#5f9dff"),
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      opacity: 0.9,
    });
    const core = new Sprite(coreMat);
    core.scale.setScalar(5);
    group.add(core);

    const shellMat = new MeshBasicMaterial({
      color: new Color("#a9c6ff"),
      wireframe: true,
      transparent: true,
      opacity: 0.5,
    });
    const shell = new Mesh(new IcosahedronGeometry(0.7, 1), shellMat);
    group.add(shell);

    const rings: Array<{ sprite: Sprite; mat: SpriteMaterial }> = [];
    for (let i = 0; i < RING_POOL; i++) {
      const mat = new SpriteMaterial({
        map: ringTexture(),
        color: new Color("#6ea8ff"),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0,
      });
      const sprite = new Sprite(mat);
      sprite.scale.setScalar(0.01);
      sprite.visible = false;
      rings.push({ sprite, mat });
    }

    return { group, coreMat, shellMat, shell, rings };
  }, []);

  const ringCursor = useRef(0);

  useFrame((_, rawDt) => {
    const dt = Math.min(rawDt, 0.05);
    const t = story.t;
    const alpha = investigatorAlpha(t);
    built.group.visible = alpha > 0.01;
    if (!built.group.visible) return;

    // position: searching → pursue
    if (t < 25) {
      investigatorPos(t, _pos);
    } else {
      investigatorPursuePos(t, _pos);
    }
    built.group.position.copy(_pos);
    built.shell.rotation.y += dt * 1.6;
    built.shell.rotation.x -= dt * 0.9;

    const pursue = investigatorPursuit(t);
    built.coreMat.opacity = alpha * (0.75 + pursue * 0.25) * (0.9 + Math.sin(t * 11) * 0.1);
    built.shellMat.opacity = alpha * 0.5;
    built.shell.scale.setScalar(1 + pursue * 0.5);
    built.group.children[0].scale.setScalar(5 + pursue * 2 + Math.sin(t * 7) * 0.3);

    // scan rings
    for (const r of built.rings) r.sprite.visible = false;
    for (const ev of SCAN_RINGS) {
      const p = (t - ev.at) / RING_LIFE;
      if (p < 0 || p > 1) continue;
      const r = built.rings[ringCursor.current++ % RING_POOL];
      r.sprite.visible = true;
      r.sprite.position.copy(_pos);
      r.sprite.scale.setScalar(1.5 + easeOutCubic(p) * 8.5);
      r.mat.opacity = (1 - p) * 0.55 * (1 - pursue * 0.6);
    }

    // arrival flash when the gap closes
    const arrive = bell(t, 27.3, 1.0);
    if (arrive > 0) built.coreMat.opacity = Math.min(1, built.coreMat.opacity + arrive * 0.5);
  });

  return (
    <group>
      <primitive object={built.group} />
      {built.rings.map((r, i) => (
        <primitive object={r.sprite} key={i} />
      ))}
    </group>
  );
}

/* --------------------------- correlation pulse ---------------------------- */

export function CorrelationPulse() {
  const built = useMemo(() => {
    const mat = new ShaderMaterial({
      vertexShader: PULSE_VERT,
      fragmentShader: PULSE_FRAG,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      side: DoubleSide, // wavefront seen from inside and out
      uniforms: {
        uColor: { value: new Color("#4f9dff") },
        uAlpha: { value: 0 },
      },
    });
    const sphere = new Mesh(new SphereGeometry(1, 42, 26), mat);
    sphere.visible = false;
    sphere.frustumCulled = false;

    const flashMat = new SpriteMaterial({
      map: glowTexture(),
      color: new Color("#bfe4ff"),
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      opacity: 0,
    });
    const flash = new Sprite(flashMat);
    flash.scale.setScalar(10);
    flash.position.set(0, 3, -14);

    return { sphere, mat, flashMat, flash };
  }, []);

  useFrame(() => {
    const t = story.t;
    const r = pulseRadius(t);
    built.sphere.visible = r > 0.05;
    if (built.sphere.visible) {
      built.sphere.scale.setScalar(r);
      built.mat.uniforms.uAlpha.value = clamp01(1 - r / 58) * 0.85;
    }
    built.flashMat.opacity = bell(t, 21.05, 1.1) * 0.85;
    const flick = 1 + Math.sin(t * 18) * 0.06;
    built.flash.scale.setScalar(10 * flick);
  });

  return (
    <group>
      <primitive object={built.sphere} />
      <primitive object={built.flash} />
    </group>
  );
}

/* -------------------------------- satellites ------------------------------ */

/** Blue intelligence nodes closing in around the stopped criminal. */
export function BlueSatellites() {
  const built = useMemo(() => {
    const stop = CRIMINAL_PATH.getPointAt((0.66 + 0.562) % 1, new Vector3());
    const sprites: Array<{ s: Sprite; m: SpriteMaterial; angle: number }> = [];
    for (let i = 0; i < SATELLITES; i++) {
      const m = new SpriteMaterial({
        map: glowTexture(),
        color: new Color("#6ea8ff"),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0,
      });
      const s = new Sprite(m);
      s.scale.setScalar(3.2);
      sprites.push({ s, m, angle: (i / SATELLITES) * Math.PI * 2 + 0.4 });
    }
    return { stop, sprites };
  }, []);

  useFrame(() => {
    const t = story.t;
    for (let i = 0; i < built.sprites.length; i++) {
      const { s, m, angle } = built.sprites[i];
      const k = satelliteK(t, i);
      const alpha = softWindow(t, 26.2 + i * 0.18, 28.3, 0.35);
      const orbit = angle + Math.max(0, t - 27.6) * 0.5;
      const radius = 11 - k * 7.6;
      _dir.set(Math.cos(orbit), Math.sin(orbit * 1.3) * 0.4, Math.sin(orbit));
      _sat.copy(built.stop).addScaledVector(_dir, radius);
      s.position.copy(_sat);
      m.opacity = alpha * 0.85;
      s.scale.setScalar(2.6 + k * 0.9 + Math.sin(t * 8 + i) * 0.25);
    }
  });

  return (
    <group>
      {built.sprites.map((r, i) => (
        <primitive object={r.s} key={i} />
      ))}
    </group>
  );
}

/* ---------------------------- trace fragments ----------------------------- */

/** Small evidence pops generated along the criminal's path as it moves. */
const TRACE_TIMES = [6.6, 8.4, 11.8, 14.2, 18.1];

export function TraceFragments() {
  const built = useMemo(() => {
    const items = TRACE_TIMES.map((at) => {
      const m = new SpriteMaterial({
        map: glowTexture(),
        color: new Color("#ffd0d0"),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0,
      });
      const s = new Sprite(m);
      s.position.copy(CRIMINAL_PATH.getPointAt(Math.max(0, criminalU(at) - 0.006), new Vector3()));
      return { s, m, at };
    });
    return items;
  }, []);

  useFrame(() => {
    const t = story.t;
    for (const it of built) {
      const p = (t - it.at) / 4.2;
      it.m.opacity = p > 0 && p < 1 ? Math.sin(Math.PI * clamp01(p)) * 0.5 : 0;
      it.s.scale.setScalar(1.8 + (p > 0 && p < 1 ? easeOutCubic(p) * 1.6 : 0));
    }
  });

  return (
    <group>
      {built.map((it, i) => (
        <primitive object={it.s} key={i} />
      ))}
    </group>
  );
}
