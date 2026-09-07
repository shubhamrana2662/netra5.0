/**
 * Connection fabric of the story graph.
 *
 *  - candidate links: creep toward each other, flare RED and break at their
 *    scripted failAt moment, then linger as faint drifting dashed lines
 *  - correlated links: drawn ON by the intelligence wavefront (cyan), stay
 *    solid with a traveling data pulse, and release during disperse
 *
 * One LineSegments draw call; per-edge state lives in dynamic attributes.
 */
import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  LineSegments,
  ShaderMaterial,
  Sprite,
  SpriteMaterial,
  Vector3,
} from "three";
import {
  CANDIDATE_EDGES,
  CORRELATED_AT,
  CORRELATED_EDGES,
  NODES,
  bell,
  clamp01,
  correlationFade,
  easeOutCubic,
  ramp,
  story,
} from "./story";
import { LINE_FRAG, LINE_VERT } from "./shaders";
import { glowTexture } from "./textures";

const RED = new Color("#ff5c5c");
const CYAN = new Color("#7fd4ff");
const _pa = new Vector3();
const _pb = new Vector3();

export function Connections() {
  const built = useMemo(() => {
    const cand = CANDIDATE_EDGES;
    const corr = CORRELATED_EDGES;
    const total = cand.length + corr.length;

    const positions = new Float32Array(total * 2 * 3);
    const aT = new Float32Array(total * 2);
    const aDash = new Float32Array(total * 2);
    const aColor = new Float32Array(total * 2 * 3);
    const aAlpha = new Float32Array(total * 2);
    const aDraw = new Float32Array(total * 2);

    const pa = new Float32Array(total * 3); // per-edge midpoint scratch for sparks
    const mid = new Float32Array(total * 3);

    let v = 0;
    const writeEdge = (ai: number, bi: number, e: number, dash: number) => {
      _pa.set(...NODES[ai].home);
      _pb.set(...NODES[bi].home);
      positions[v * 3] = _pa.x; positions[v * 3 + 1] = _pa.y; positions[v * 3 + 2] = _pa.z;
      positions[v * 3 + 3] = _pb.x; positions[v * 3 + 4] = _pb.y; positions[v * 3 + 5] = _pb.z;
      aT[v] = 0; aT[v + 1] = 1;
      aDash[v] = dash; aDash[v + 1] = dash;
      pa[e * 3] = _pa.x; pa[e * 3 + 1] = _pa.y; pa[e * 3 + 2] = _pa.z;
      mid[e * 3] = (_pa.x + _pb.x) / 2;
      mid[e * 3 + 1] = (_pa.y + _pb.y) / 2;
      mid[e * 3 + 2] = (_pa.z + _pb.z) / 2;
      v += 2;
    };

    cand.forEach((ed, i) => writeEdge(ed.a, ed.b, i, 1));
    corr.forEach(([ai, bi], i) => writeEdge(ai, bi, cand.length + i, 0));

    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(positions, 3));
    geometry.setAttribute("aT", new BufferAttribute(aT, 1));
    geometry.setAttribute("aDash", new BufferAttribute(aDash, 1));
    geometry.setAttribute("aColor", new BufferAttribute(aColor, 3));
    geometry.setAttribute("aAlpha", new BufferAttribute(aAlpha, 1));
    geometry.setAttribute("aDraw", new BufferAttribute(aDraw, 1));
    geometry.boundingSphere = null;

    const material = new ShaderMaterial({
      vertexShader: LINE_VERT,
      fragmentShader: LINE_FRAG,
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
      uniforms: { uTime: { value: 0 } },
    });

    const lines = new LineSegments(geometry, material);
    lines.frustumCulled = false;

    // one spark sprite per candidate edge, invisible until its fail moment
    const sparkMat = () =>
      new SpriteMaterial({
        map: glowTexture(),
        color: RED,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0,
      });
    const sparks = cand.map((_, i) => {
      const s = new Sprite(sparkMat());
      s.scale.setScalar(3.2);
      s.position.set(mid[i * 3], mid[i * 3 + 1], mid[i * 3 + 2]);
      s.frustumCulled = false;
      return s;
    });

    return { lines, geometry, material, aColor, aAlpha, aDraw, sparks, candCount: cand.length, corrCount: corr.length };
  }, []);

  useFrame(() => {
    const t = story.t;
    built.material.uniforms.uTime.value = t;
    const { aColor, aAlpha, aDraw, candCount, corrCount } = built;

    // ---- candidate (broken) edges
    for (let e = 0; e < candCount; e++) {
      const ed = CANDIDATE_EDGES[e];
      const fail = ed.failAt;
      const flash = bell(t, fail, 0.7);
      const creep = ramp(t, Math.max(0, fail - 3.2), fail) * 0.42; // advance then die
      const postFail = t > fail;
      const draw = postFail ? 0.3 + Math.sin(e * 2.1) * 0.04 : 0.06 + creep;
      const alpha = postFail
        ? (0.13 + Math.sin(t * 1.7 + e * 2.4) * 0.045) * (1 - clamp01((t - 21) / 9) * 0.55)
        : 0.14 + flash * 0.75;
      const cR = RED.r, cG = RED.g, cB = RED.b;

      for (let k = 0; k < 2; k++) {
        const vi = e * 2 + k;
        aColor[vi * 3] = cR; aColor[vi * 3 + 1] = cG; aColor[vi * 3 + 2] = cB;
        aAlpha[vi] = alpha;
        aDraw[vi] = draw;
      }
      built.sparks[e].material.opacity = flash * 0.9;
      built.sparks[e].scale.setScalar(2.2 + flash * 2.6);
    }

    // ---- correlated edges (drawn on by the pulse)
    for (let i = 0; i < corrCount; i++) {
      const at = CORRELATED_AT[i];
      const on = easeOutCubic(ramp(t, at, at + 1.0)) * correlationFade(t);
      const drawIn = ramp(t, at, at + 1.0);
      const alpha = on * (0.45 + bell(t, at, 1.2) * 0.45);
      const vi = (candCount + i) * 2;
      for (let k = 0; k < 2; k++) {
        aColor[(vi + k) * 3] = CYAN.r;
        aColor[(vi + k) * 3 + 1] = CYAN.g;
        aColor[(vi + k) * 3 + 2] = CYAN.b;
        aAlpha[vi + k] = alpha;
        aDraw[vi + k] = drawIn;
      }
    }

    built.geometry.attributes.aColor.needsUpdate = true;
    built.geometry.attributes.aAlpha.needsUpdate = true;
    built.geometry.attributes.aDraw.needsUpdate = true;
  });

  return (
    <group>
      <primitive object={built.lines} />
      {built.sparks.map((s, i) => (
        <primitive object={s} key={i} />
      ))}
    </group>
  );
}
