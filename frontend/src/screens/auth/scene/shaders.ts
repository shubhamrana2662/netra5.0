/**
 * GLSL for the login world. Kept minimal and GPU-friendly:
 *  - particles: positions drift on closed periodic paths (seamless loop)
 *  - trail:     age-faded point sprites (ring buffer written on CPU)
 *  - lines:     per-edge draw-on progress, dash state, traveling data pulse
 *  - pulse:     fresnel intelligence wavefront
 *  - grid:      digital terrain with a periodic scan band
 *  - city:      instanced towers with rim glow
 */

/* -------------------------------- particles ------------------------------- */

export const PARTICLE_VERT = /* glsl */ `
  attribute float aScale;
  attribute vec3 aSeed;      // per-particle phases in [0,1)
  uniform float uTime;       // loop time in seconds
  uniform float uLoop;       // loop length in seconds
  uniform float uPixelRatio;
  varying float vAlpha;

  void main() {
    vec3 p = position;
    float w = 6.28318530718;
    float k1 = floor(aSeed.x * 3.0) + 1.0;   // integer cycles per loop → seamless
    float k2 = floor(aSeed.y * 2.0) + 1.0;
    float k3 = floor(aSeed.z * 3.0) + 1.0;
    p.x += sin(w * k1 * uTime / uLoop + aSeed.x * 31.4) * 1.8;
    p.y += sin(w * k2 * uTime / uLoop + aSeed.y * 17.3) * 1.3;
    p.z += sin(w * k3 * uTime / uLoop + aSeed.z * 23.7) * 1.8;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_PointSize = aScale * uPixelRatio * (150.0 / max(1.0, -mv.z));
    vAlpha = 0.30 + 0.70 * (0.5 + 0.5 * sin(w * (k2 + k3) * uTime / uLoop + aSeed.x * 41.9));
    gl_Position = projectionMatrix * mv;
  }
`;

export const PARTICLE_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uOpacity;
  varying float vAlpha;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.06, d);
    gl_FragColor = vec4(uColor, a * vAlpha * uOpacity);
  }
`;

/* ---------------------------------- trail --------------------------------- */

export const TRAIL_VERT = /* glsl */ `
  attribute float aBirth;
  attribute float aLife;
  attribute float aScale;
  uniform float uTime;
  uniform float uPixelRatio;
  varying float vFade;

  void main() {
    float age = uTime - aBirth;
    vFade = clamp(1.0 - age / max(0.001, aLife), 0.0, 1.0);
    vFade *= vFade;
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    float grow = 1.0 + (1.0 - vFade) * 1.6;
    gl_PointSize = aScale * grow * uPixelRatio * (150.0 / max(1.0, -mv.z));
    gl_Position = projectionMatrix * mv;
  }
`;

export const TRAIL_FRAG = /* glsl */ `
  uniform vec3 uColor;
  varying float vFade;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float a = smoothstep(0.5, 0.05, d) * vFade;
    gl_FragColor = vec4(uColor, a);
  }
`;

/* ---------------------------------- lines --------------------------------- */
// attributes: aT (0..1 along edge), aColor, aAlpha, aDraw (draw-on progress),
// aDash (1 = dashed/broken, 0 = solid)
export const LINE_VERT = /* glsl */ `
  attribute float aT;
  attribute vec3 aColor;
  attribute float aAlpha;
  attribute float aDraw;
  attribute float aDash;
  varying float vT;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vDraw;
  varying float vDash;

  void main() {
    vT = aT; vColor = aColor; vAlpha = aAlpha; vDraw = aDraw; vDash = aDash;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

export const LINE_FRAG = /* glsl */ `
  uniform float uTime;
  varying float vT;
  varying vec3 vColor;
  varying float vAlpha;
  varying float vDraw;
  varying float vDash;

  void main() {
    // draw-on: only render the portion already traced
    if (vT > vDraw) discard;
    float head = (vDraw < 0.999) ? smoothstep(vDraw, vDraw - 0.07, vT) : 1.0;

    // broken links render as dashes drifting to a halt
    if (vDash > 0.5) {
      float seg = fract(vT * 9.0 - uTime * 0.18);
      if (seg > 0.55) discard;
    }

    // traveling data pulse on solid (correlated) edges
    float flow = 0.0;
    if (vDash < 0.5) {
      float p = fract(vT * 0.5 - uTime * 0.045);
      flow = exp(-90.0 * (p - 0.5) * (p - 0.5)) * 0.9;
    }

    gl_FragColor = vec4(vColor + vec3(flow * 0.35), vAlpha * head * (0.85 + flow));
  }
`;

/* ----------------------------- pulse wavefront ---------------------------- */

export const PULSE_VERT = /* glsl */ `
  varying vec3 vN;
  varying vec3 vV;
  void main() {
    vec4 mv = modelViewMatrix * vec4(position, 1.0);
    vN = normalize(normalMatrix * normal);
    vV = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

export const PULSE_FRAG = /* glsl */ `
  uniform vec3 uColor;
  uniform float uAlpha;
  varying vec3 vN;
  varying vec3 vV;

  void main() {
    float rim = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.4);
    gl_FragColor = vec4(uColor * (rim * 1.7 + 0.05), rim * uAlpha);
  }
`;

/* ---------------------------------- grid ---------------------------------- */

export const GRID_VERT = /* glsl */ `
  varying vec2 vXZ;
  varying vec2 vUv;
  void main() {
    vUv = uv;
    vec4 world = modelMatrix * vec4(position, 1.0);
    vXZ = world.xz;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

export const GRID_FRAG = /* glsl */ `
  uniform float uTime;
  uniform float uLoop;
  uniform vec3 uColor;
  uniform float uOpacity;
  varying vec2 vXZ;
  varying vec2 vUv;

  void main() {
    vec2 coord = vXZ / 9.0;
    vec2 grid = abs(fract(coord - 0.5) - 0.5) / fwidth(coord);
    float line = 1.0 - min(min(grid.x, grid.y), 1.0);

    // radial fade so the terrain dissolves into fog
    float fade = smoothstep(0.52, 0.10, length(vUv - 0.5));

    // periodic scan band sweeping across the terrain (one pass per loop)
    float bandZ = mix(-160.0, 160.0, fract(uTime / uLoop));
    float band = exp(-0.006 * abs(vXZ.y - bandZ) * abs(vXZ.y - bandZ) / 8.0) * 0.5;

    float a = (line * (0.22 + band) + band * 0.10) * fade * uOpacity;
    gl_FragColor = vec4(uColor, a);
  }
`;

/* ---------------------------------- city ---------------------------------- */

export const CITY_VERT = /* glsl */ `
  varying vec3 vN;
  varying vec3 vV;
  varying vec3 vLocal;
  varying float vHash;
  void main() {
    vec4 world = instanceMatrix * vec4(position, 1.0);
    vec4 mv = modelViewMatrix * world;
    vN = normalize(normalMatrix * (instanceMatrix * vec4(normal, 0.0)).xyz);
    vV = normalize(-mv.xyz);
    vLocal = position;
    vHash = fract(sin(dot(instanceMatrix[3].xz, vec2(12.9898, 78.233))) * 43758.5453);
    gl_Position = projectionMatrix * mv;
  }
`;

export const CITY_FRAG = /* glsl */ `
  uniform vec3 uBase;
  uniform vec3 uGlow;
  varying vec3 vN;
  varying vec3 vV;
  varying vec3 vLocal;
  varying float vHash;

  void main() {
    float rim = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 3.0);
    float top = smoothstep(0.45, 0.5, vLocal.y);          // roof highlight
    float window = step(0.985, fract(vLocal.y * 3.0 + vHash * 17.0))
                 * step(0.6, fract(vLocal.x * 2.0 + vLocal.z * 2.0 + vHash * 7.0));
    vec3 col = uBase
      + uGlow * (rim * 0.55 + top * 0.10 + window * 0.35) * (0.6 + vHash * 0.8);
    gl_FragColor = vec4(col, 1.0);
  }
`;
