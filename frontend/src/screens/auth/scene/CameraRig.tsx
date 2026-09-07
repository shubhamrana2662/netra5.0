/**
 * Cinematic camera: a closed spline (one lap per loop — inherently seamless)
 * blended with story-driven look targets and small damped mouse parallax.
 */
import { useFrame, useThree } from "@react-three/fiber";
import { useRef } from "react";
import { Vector3 } from "three";
import {
  LOOP,
  cameraChaseWeight,
  cameraPos,
  cameraTension,
  criminalAlpha,
  criminalPos,
  LOOK_CENTER,
  story,
} from "./story";
import { quality } from "./quality";

const _pos = new Vector3();
const _look = new Vector3();
const _criminal = new Vector3();
const _parallax = new Vector3();
const _lookTarget = new Vector3();

export function CameraRig() {
  const camera = useThree((s) => s.camera);
  const smoothPointer = useRef({ x: 0, y: 0 });

  useFrame((state, rawDt) => {
    const t = story.t;
    const dt = Math.min(rawDt, 0.05);
    const damp = 1 - Math.exp(-4.5 * dt);

    // ---- base spline position
    cameraPos(t, _pos);

    // ---- look target: evidence centroid, leaning toward the fleeing criminal
    _look.copy(LOOK_CENTER);
    const chase = cameraChaseWeight(t);
    if (chase > 0.001 && criminalAlpha(t) > 0.01) {
      criminalPos(t, _criminal);
      _look.lerp(_criminal, chase * 0.72);
    }

    // ---- story dolly: lean in during the correlation-failure peak,
    //      pull back while the intelligence wave connects the graph
    const tension = cameraTension(t);
    if (tension > 0.001) {
      _parallax.copy(_pos).sub(_look).normalize().multiplyScalar(-6 * tension);
      _pos.add(_parallax);
    }
    const pull = Math.max(0, Math.sin((Math.PI * Math.min(1, Math.max(0, (t - 21) / 4)))) * (t > 21 && t < 25 ? 1 : 0));
    if (pull > 0.001) {
      _parallax.copy(_pos).sub(_look).normalize().multiplyScalar(9 * pull);
      _pos.add(_parallax);
      _pos.y += 3 * pull;
    }

    // ---- mouse parallax (desktop, high tier): subtle, damped
    if (!quality.isMobileLike()) {
      const px = state.pointer.x;
      const py = state.pointer.y;
      smoothPointer.current.x += (px - smoothPointer.current.x) * damp;
      smoothPointer.current.y += (py - smoothPointer.current.y) * damp;
      const mx = smoothPointer.current.x;
      const my = smoothPointer.current.y;
      // lateral sway relative to view direction
      _parallax.set(mx * 2.6, -my * 1.6, 0).applyQuaternion(camera.quaternion);
      _pos.add(_parallax);
      _look.x += mx * 3.2;
      _look.y += my * 1.4;
    }

    camera.position.lerp(_pos, 1 - Math.exp(-6.0 * dt));
    camera.lookAt(_look);

    // tiny roll adds documentary tension at the failure peak
    if (tension > 0.001) camera.rotateZ(0.02 * tension + smoothPointer.current.x * 0.008);

    // keep the loop breathing even if something hiccupped
    if (!Number.isFinite(camera.position.x)) camera.position.set(36, 12, 30);
    void LOOP;
  });

  return null;
}
