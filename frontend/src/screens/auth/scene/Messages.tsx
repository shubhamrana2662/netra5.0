/**
 * Environmental system messages — brief mono captions that live inside the
 * world near the objects they describe, fading in and out on the story clock.
 */
import { useFrame } from "@react-three/fiber";
import { useMemo } from "react";
import { Color, Sprite, SpriteMaterial } from "three";
import { MESSAGES, story } from "./story";
import { messageTexture } from "./textures";

export function WorldMessages() {
  const built = useMemo(
    () =>
      MESSAGES.map((msg) => {
        const mat = new SpriteMaterial({
          map: messageTexture(msg.text, msg.color),
          color: new Color("#ffffff"),
          transparent: true,
          depthWrite: false,
          opacity: 0,
        });
        const sprite = new Sprite(mat);
        sprite.position.set(...msg.pos);
        sprite.scale.set(13.5, 2.1, 1);
        sprite.frustumCulled = false;
        return { sprite, mat, msg };
      }),
    [],
  );

  useFrame(() => {
    const t = story.t;
    for (const b of built) {
      const p = (t - b.msg.at) / b.msg.hold;
      // envelope: 0.5s in, hold, 0.6s out, gentle upward drift
      const a = p > 0 && p < 1 ? Math.min(1, p / 0.16, (1 - p) / 0.2) : 0;
      b.mat.opacity = Math.max(0, a) * 0.92;
      b.sprite.position.y = b.msg.pos[1] + (p > 0 && p < 1 ? p * 0.9 : 0);
    }
  });

  return (
    <group>
      {built.map((b, i) => (
        <primitive object={b.sprite} key={i} />
      ))}
    </group>
  );
}
