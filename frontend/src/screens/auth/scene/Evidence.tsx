/**
 * Evidence field: holographic octahedron nodes with data cards and labels.
 * Pre-correlation everything reads neutral cool-gray; the CyberDrishti pulse
 * turns relevant nodes cyan, flashes them, and lets noise fade out.
 * Cursor proximity gently boosts glow/labels — atmospheric, not clickable.
 */
import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import {
  AdditiveBlending,
  Color,
  Group,
  Mesh,
  OctahedronGeometry,
  Raycaster,
  ShaderMaterial,
  Sprite,
  SpriteMaterial,
  Vector3,
} from "three";
import { CARDS, NODES, bell, clamp01, easeOutCubic, ramp, story } from "./story";
import { quality } from "./quality";
import { cardTexture, glowTexture, labelTexture } from "./textures";

const NODE_VERT = /* glsl */ `
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

const NODE_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uBoost;   // cursor proximity 0..1
  uniform float uFlash;   // activation flash 0..1
  varying vec3 vN;
  varying vec3 vV;

  void main() {
    float ndv = abs(dot(normalize(vN), normalize(vV)));
    float rim = pow(1.0 - ndv, 1.9);
    float core = pow(ndv, 2.2);
    vec3 col = uColor * (rim * 1.55 + 0.10 + core * 0.22) + vec3(0.6, 0.9, 1.0) * uFlash * rim;
    float a = rim * (0.85 + uBoost * 0.15) + 0.10 + uFlash * 0.25;
    gl_FragColor = vec4(col, a);
  }
`;

const IDLE_COLOR = new Color("#b9c7dd");
const ACTIVE_COLOR = new Color("#7fd4ff");
const NOISE_COLOR = new Color("#42506b");

interface NodeObj {
  group: Group;
  mesh: Mesh;
  glow: Sprite;
  mat: ShaderMaterial;
  glowMat: SpriteMaterial;
  labelMat: SpriteMaterial;
  cardMat: SpriteMaterial | null;
  home: Vector3;
  seed: number;
  noise: boolean;
  activationAt: number;
  boost: number;
}

export function EvidenceField() {
  const raycaster = useMemo(() => new Raycaster(), []);
  const camera = useThree((s) => s.camera);
  const gl = useThree((s) => s.gl);
  const maxAniso = useMemo(() => Math.min(8, gl.capabilities.getMaxAnisotropy()), [gl]);

  const objs = useMemo<NodeObj[]>(() => {
    const geo = new OctahedronGeometry(0.95, 0);
    return NODES.map((node) => {
      const group = new Group();
      group.position.set(...node.home);

      const mat = new ShaderMaterial({
        vertexShader: NODE_VERT,
        fragmentShader: NODE_FRAG,
        transparent: true,
        uniforms: {
          uColor: { value: IDLE_COLOR.clone() },
          uBoost: { value: 0 },
          uFlash: { value: 0 },
        },
      });
      const mesh = new Mesh(geo, mat);
      group.add(mesh);

      const glowMat = new SpriteMaterial({
        map: glowTexture(),
        color: new Color(node.noise ? "#8fa4c4" : "#8fd0ff"),
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
        opacity: 0.35,
      });
      const glow = new Sprite(glowMat);
      glow.scale.setScalar(5.2);
      group.add(glow);

      const labelMat = new SpriteMaterial({
        map: labelTexture(node.label),
        transparent: true,
        depthWrite: false,
        opacity: 0.5,
      });
      labelMat.map!.anisotropy = maxAniso;
      const label = new Sprite(labelMat);
      label.scale.set(6.4, 1.2, 1);
      label.position.y = 2.4;
      group.add(label);

      const cardDef = CARDS[node.id];
      let cardMat: SpriteMaterial | null = null;
      if (cardDef) {
        cardMat = new SpriteMaterial({
          map: cardTexture(node.label, cardDef.lines),
          transparent: true,
          depthWrite: false,
          opacity: 0.85,
        });
        cardMat.map!.anisotropy = maxAniso;
        const card = new Sprite(cardMat);
        card.scale.set(7.6, 4.75, 1);
        // offset cards to a stable side so they never cover their node
        const side = node.seed > 0.5 ? 1 : -1;
        card.position.set(side * 6.6, 1.4 + (node.seed - 0.5) * 3.2, 0);
        group.add(card);
      }

      return {
        group, mesh, glow, mat, glowMat, labelMat, cardMat,
        home: new Vector3(...node.home),
        seed: node.seed,
        noise: node.noise,
        activationAt: node.activationAt,
        boost: 0,
      };
    });
  }, [maxAniso]);

  useFrame((state) => {
    const t = story.t;
    const pointerActive = !quality.isMobileLike() && (state.pointer.x !== 0 || state.pointer.y !== 0);

    for (const o of objs) {
      const s = o.seed;

      // floating bob — integer cycles per loop keep it seamless
      o.group.position.y = o.home.y + Math.sin((t / 30) * Math.PI * 2 * (1 + Math.floor(s * 2)) + s * 31.4) * 0.7;
      o.group.rotation.y = t * (0.14 + s * 0.1) + s * 6.28;
      o.group.rotation.x = Math.sin((t / 30) * Math.PI * 2 + s * 9.4) * 0.18;

      // activation state
      const act = easeOutCubic(ramp(t, o.activationAt, o.activationAt + 0.9));
      const flash = bell(t, o.activationAt, 1.1);
      const noiseFade = o.noise ? 1 - act * 0.88 : 1;

      // cursor proximity
      let boostTarget = 0;
      if (pointerActive) {
        raycaster.setFromCamera(state.pointer, camera);
        const d = raycaster.ray.distanceToPoint(o.home);
        boostTarget = clamp01(1 - d / 5.5);
      }
      o.boost += (boostTarget - o.boost) * 0.12;

      // color: neutral gray → cyan when the pulse arrives; noise dims away
      o.mat.uniforms.uColor.value.copy(o.noise ? (act > 0.5 ? NOISE_COLOR : IDLE_COLOR) : IDLE_COLOR);
      if (!o.noise) o.mat.uniforms.uColor.value.lerp(ACTIVE_COLOR, act);
      o.mat.uniforms.uBoost.value = o.boost;
      o.mat.uniforms.uFlash.value = flash;

      // mesh pop + glow
      o.mesh.scale.setScalar(1 + flash * 0.55 + act * 0.18);
      o.glowMat.opacity = (0.20 + act * 0.30 + o.boost * 0.22 + flash * 0.5) * noiseFade;
      o.glow.scale.setScalar(4.6 + o.boost * 2.4 + flash * 3.2 + act * 0.9);

      // labels & cards
      o.labelMat.opacity = (0.42 + o.boost * 0.5 + act * 0.12) * noiseFade;
      if (o.cardMat) {
        const base = 0.8;
        const resolved = o.noise ? 0.05 : 0.16;
        o.cardMat.opacity = (base + (resolved - base) * act + o.boost * 0.18) * (o.noise ? 1 - act * 0.9 : 1);
      }
    }
  });

  return (
    <group>
      {objs.map((o) => (
        <primitive object={o.group} key={o.activationAt + o.seed} />
      ))}
    </group>
  );
}
