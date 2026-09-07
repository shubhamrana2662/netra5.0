/**
 * Deep environment: instanced data-city, glowing terrain grid, volumetric-feel
 * light planes, ambient particle field and large foreground bokeh for depth.
 */
import { useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import {
  AdditiveBlending,
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  Object3D,
  PlaneGeometry,
  Points,
  ShaderMaterial,
  Sprite,
  SpriteMaterial,
} from "three";
import { LOOP, story } from "./story";
import { quality } from "./quality";
import {
  CITY_FRAG,
  CITY_VERT,
  GRID_FRAG,
  GRID_VERT,
  PARTICLE_FRAG,
  PARTICLE_VERT,
} from "./shaders";
import { glowTexture } from "./textures";

/** Upper bounds used at build time; runtime counts come from quality.count(). */
const COUNT_MAX = {
  city: 340,
  particles: 2600,
  dust: 30,
};

/** Deterministic PRNG so the city is identical every load. */
function mulberry32(seed: number) {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/* --------------------------------- city ----------------------------------- */

export function DigitalCity() {
  const geometry = useMemo(() => new BoxGeometry(1, 1, 1), []);
  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: CITY_VERT,
        fragmentShader: CITY_FRAG,
        uniforms: {
          uBase: { value: new Color("#0a1220") },
          uGlow: { value: new Color("#3d6fb0") },
        },
      }),
    [],
  );

  const mesh = useMemo(() => {
    const rand = mulberry32(1101);
    const inst = new InstancedMesh(geometry, material, COUNT_MAX.city);
    const o = new Object3D();
    for (let i = 0; i < COUNT_MAX.city; i++) {
      // ring bands around the evidence cloud, denser far away
      const band = rand();
      const radius = 64 + band * band * 95 + rand() * 22;
      const angle = rand() * Math.PI * 2;
      const w = 2.4 + rand() * 6.5;
      const d = 2.4 + rand() * 6.5;
      const h = 3 + Math.pow(rand(), 1.6) * 30;
      o.position.set(Math.cos(angle) * radius, -16 + h / 2, Math.sin(angle) * radius - 14);
      o.scale.set(w, h, d);
      o.rotation.y = rand() * Math.PI;
      o.updateMatrix();
      inst.setMatrixAt(i, o.matrix);
    }
    inst.instanceMatrix.needsUpdate = true;
    inst.frustumCulled = false;
    return inst;
  }, [geometry, material]);

  useFrame(() => {
    mesh.count = quality.count("city");
  });

  return <primitive object={mesh} />;
}

/* ------------------------------- grid floor ------------------------------- */

const GRID_SIZE = 620;

export function DigitalTerrain() {
  const geometry = useMemo(() => new PlaneGeometry(GRID_SIZE, GRID_SIZE, 1, 1).rotateX(-Math.PI / 2), []);
  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: GRID_VERT,
        fragmentShader: GRID_FRAG,
        transparent: true,
        depthWrite: false,
        side: DoubleSide,
        uniforms: {
          uTime: { value: 0 },
          uLoop: { value: LOOP },
          uColor: { value: new Color("#2e5f9e") },
          uOpacity: { value: 0.85 },
        },
      }),
    [],
  );

  useFrame(() => {
    material.uniforms.uTime.value = story.t;
  });

  return (
    <mesh geometry={geometry} material={material} position={[0, -16, -14]} frustumCulled={false} />
  );
}

/* ----------------------------- volumetric haze ---------------------------- */

/** Two huge additive gradient planes behind the city — cheap volumetric haze. */
export function VolumetricHaze() {
  const material = useMemo(
    () =>
      new ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        side: DoubleSide,
        uniforms: { uColor: { value: new Color("#1d4a8c") }, uTime: { value: 0 } },
        vertexShader: /* glsl */ `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 uColor;
          uniform float uTime;
          varying vec2 vUv;
          void main() {
            float vertical = smoothstep(0.0, 0.55, vUv.y) * smoothstep(1.0, 0.62, vUv.y);
            float sway = 0.9 + 0.1 * sin(uTime * 0.5);
            gl_FragColor = vec4(uColor, vertical * 0.05 * sway);
          }
        `,
      }),
    [],
  );

  useFrame(() => {
    material.uniforms.uTime.value = story.t;
  });

  return (
    <group>
      <mesh material={material} position={[0, 6, -95]} frustumCulled={false}>
        <planeGeometry args={[340, 130]} />
      </mesh>
      <mesh material={material} position={[-70, 2, 40]} rotation-y={1.2} frustumCulled={false}>
        <planeGeometry args={[260, 110]} />
      </mesh>
    </group>
  );
}

/* ---------------------------- ambient particles --------------------------- */

export function AmbientParticles() {
  const geometry = useMemo(() => {
    const rand = mulberry32(77);
    const pos = new Float32Array(COUNT_MAX.particles * 3);
    const scale = new Float32Array(COUNT_MAX.particles);
    const seed = new Float32Array(COUNT_MAX.particles * 3);
    for (let i = 0; i < COUNT_MAX.particles; i++) {
      pos[i * 3] = (rand() - 0.5) * 230;
      pos[i * 3 + 1] = -14 + rand() * 90;
      pos[i * 3 + 2] = -14 + (rand() - 0.5) * 230;
      scale[i] = 0.5 + Math.pow(rand(), 2.2) * 2.6;
      seed[i * 3] = rand();
      seed[i * 3 + 1] = rand();
      seed[i * 3 + 2] = rand();
    }
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(pos, 3));
    g.setAttribute("aScale", new BufferAttribute(scale, 1));
    g.setAttribute("aSeed", new BufferAttribute(seed, 3));
    return g;
  }, []);

  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: PARTICLE_VERT,
        fragmentShader: PARTICLE_FRAG,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        uniforms: {
          uTime: { value: 0 },
          uLoop: { value: LOOP },
          uPixelRatio: { value: 1 },
          uColor: { value: new Color("#9fc4f5") },
          uOpacity: { value: 0.75 },
        },
      }),
    [],
  );

  const points = useMemo(() => {
    const p = new Points(geometry, material);
    p.frustumCulled = false;
    return p;
  }, [geometry, material]);

  const gl = useThree((s) => s.gl);

  useFrame(() => {
    material.uniforms.uTime.value = story.t;
    material.uniforms.uPixelRatio.value = Math.min(gl.getPixelRatio(), quality.dprMax());
    // degrade/upgrade takes effect immediately
    geometry.setDrawRange(0, quality.count("particles"));
  });

  return <primitive object={points} />;
}

/* ---------------------------- foreground dust ----------------------------- */

/** Large soft bokeh sprites drifting near the camera path — layer-1 depth cue. */
export function ForegroundDust() {
  const group = useRef<Group>(null);

  const items = useMemo(() => {
    const rand = mulberry32(4242);
    return Array.from({ length: COUNT_MAX.dust }, (_, i) => ({
      radius: 40 + rand() * 16,
      angle: rand() * Math.PI * 2,
      y: -6 + rand() * 22,
      speed: (0.5 + rand() * 1.2) * (i % 2 ? 1 : -1),
      scale: 4 + rand() * 9,
      phase: rand() * Math.PI * 2,
      opacity: 0.028 + rand() * 0.03,
    }));
  }, []);

  const baseMaterial = useMemo(
    () =>
      new SpriteMaterial({
        map: glowTexture(),
        color: new Color("#6f9fe0"),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0.04,
      }),
    [],
  );

  const sprites = useMemo(
    () =>
      items.map((it) => {
        const s = new Sprite(baseMaterial.clone());
        s.material.opacity = it.opacity;
        s.scale.setScalar(it.scale);
        return s;
      }),
    [items, baseMaterial],
  );

  useFrame(() => {
    const t = story.t;
    items.forEach((it, i) => {
      const a = it.angle + Math.sin((t / LOOP) * Math.PI * 2 * it.speed + it.phase) * 1.6;
      sprites[i].position.set(
        Math.cos(a) * it.radius,
        it.y + Math.sin((t / LOOP) * Math.PI * 4 + it.phase) * 1.8,
        Math.sin(a) * it.radius - 14,
      );
    });
  });

  return (
    <group ref={group}>
      {sprites.map((s, i) => (
        <primitive object={s} key={i} />
      ))}
    </group>
  );
}
