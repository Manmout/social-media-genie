# Remotion Cinematic Animation Patterns

Reference doc for transforming flat "text on dark background" into alive, dynamic videos.
Researched 2026-03-27 from remotion.dev docs, GitHub skills repo, community guides.

---

## 1. Spring Presets (beyond defaults)

The default `spring()` is mushy. Use these tuned configs:

```tsx
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';

const frame = useCurrentFrame();
const { fps } = useVideoConfig();

// PUNCHY POP-IN — fast arrival, slight overshoot, snaps into place
const punchyScale = spring({
  frame, fps,
  config: { mass: 0.4, damping: 12, stiffness: 200 },
});

// HEAVY DROP — slow, weighty, no bounce (titles)
const heavyDrop = spring({
  frame, fps,
  config: { mass: 2, damping: 20, stiffness: 80, overshootClamping: true },
});

// ELASTIC BOUNCE — playful, overshoots then settles (icons, emojis)
const elastic = spring({
  frame, fps,
  config: { mass: 0.6, damping: 6, stiffness: 150 },
});

// SMOOTH EASE-IN — gentle, no bounce (backgrounds, fades)
const smooth = spring({
  frame, fps,
  config: { mass: 1, damping: 30, stiffness: 100, overshootClamping: true },
});

// SNAPPY — instant arrival for UI elements
const snappy = spring({
  frame, fps,
  config: { mass: 0.3, damping: 15, stiffness: 300 },
});
```

Use `delay` param for staggered entrances:
```tsx
const item1 = spring({ frame, fps, delay: 0, config: { mass: 0.4, damping: 12, stiffness: 200 } });
const item2 = spring({ frame, fps, delay: 5, config: { mass: 0.4, damping: 12, stiffness: 200 } });
const item3 = spring({ frame, fps, delay: 10, config: { mass: 0.4, damping: 12, stiffness: 200 } });
```

Use `durationInFrames` to stretch/compress any spring to exact timing:
```tsx
const stretched = spring({ frame, fps, durationInFrames: 60, config: { stiffness: 100 } });
```

Playground: https://www.remotion.dev/timing-editor

---

## 2. Character-by-Character Text Animation

### Approach A: Typewriter (string slicing)
```tsx
const TypewriterText: React.FC<{ text: string; startFrame?: number }> = ({
  text, startFrame = 0,
}) => {
  const frame = useCurrentFrame();
  const charsPerFrame = 0.5; // adjust speed
  const elapsed = Math.max(0, frame - startFrame);
  const visibleChars = Math.min(text.length, Math.floor(elapsed * charsPerFrame));
  const displayText = text.slice(0, visibleChars);

  // Blinking cursor
  const showCursor = Math.floor(frame / 15) % 2 === 0;

  return (
    <span style={{ fontFamily: 'monospace', fontSize: 48, color: 'white' }}>
      {displayText}
      {showCursor && <span style={{ opacity: 0.8 }}>|</span>}
    </span>
  );
};
```

### Approach B: Per-character spring (kinetic typography)
```tsx
const KineticText: React.FC<{ text: string; staggerFrames?: number }> = ({
  text, staggerFrames = 3,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ display: 'flex', overflow: 'hidden' }}>
      {text.split('').map((char, i) => {
        const charSpring = spring({
          frame,
          fps,
          delay: i * staggerFrames,
          config: { mass: 0.4, damping: 12, stiffness: 200 },
        });

        return (
          <span
            key={i}
            style={{
              display: 'inline-block',
              opacity: charSpring,
              transform: `translateY(${(1 - charSpring) * 40}px) scale(${0.5 + charSpring * 0.5})`,
              // Each char drops in from above and scales up
            }}
          >
            {char === ' ' ? '\u00A0' : char}
          </span>
        );
      })}
    </div>
  );
};
```

### Approach C: Word-by-word reveal
```tsx
const WordReveal: React.FC<{ text: string; staggerFrames?: number }> = ({
  text, staggerFrames = 8,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(' ');

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
      {words.map((word, i) => {
        const wordSpring = spring({
          frame, fps,
          delay: i * staggerFrames,
          config: { mass: 0.5, damping: 14, stiffness: 180 },
        });
        return (
          <span
            key={i}
            style={{
              opacity: wordSpring,
              transform: `translateX(${(1 - wordSpring) * -30}px)`,
              filter: `blur(${(1 - wordSpring) * 4}px)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};
```

### Third-party packages
- `remotion-animate-text` — animate chars/words on CSS properties (opacity, scale, x, y, rotate)
- `@remotion/text-warping` — warp text along paths
- `remotion-morph-text` — morphing between two text strings

---

## 3. Animated Backgrounds

### A: Moving gradient (pure CSS, frame-driven)
```tsx
const AnimatedGradient: React.FC = () => {
  const frame = useCurrentFrame();
  const angle = (frame * 1.5) % 360; // slow rotation

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${angle}deg, #0f0c29, #302b63, #24243e)`,
      }}
    />
  );
};
```

### B: Pulsing radial gradient
```tsx
const PulsingGradient: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pulse = spring({
    frame: frame % (fps * 2), // loop every 2s
    fps,
    config: { mass: 1, damping: 15, stiffness: 40 },
  });
  const size = 40 + pulse * 20; // 40% to 60%

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% 50%, rgba(99,102,241,0.4) 0%, transparent ${size}%)`,
        backgroundColor: '#0a0a0a',
      }}
    />
  );
};
```

### C: Mesh gradient (multiple blobs)
```tsx
const MeshGradient: React.FC = () => {
  const frame = useCurrentFrame();
  const blobs = [
    { color: 'rgba(99,102,241,0.3)', cx: 30, cy: 30, speed: 0.8 },
    { color: 'rgba(236,72,153,0.3)', cx: 70, cy: 60, speed: 1.2 },
    { color: 'rgba(16,185,129,0.25)', cx: 50, cy: 80, speed: 0.6 },
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: '#0f172a', overflow: 'hidden' }}>
      {blobs.map((blob, i) => {
        const x = blob.cx + Math.sin(frame * 0.02 * blob.speed + i) * 15;
        const y = blob.cy + Math.cos(frame * 0.015 * blob.speed + i * 2) * 10;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${y}%`,
              width: 600,
              height: 600,
              borderRadius: '50%',
              background: blob.color,
              filter: 'blur(80px)',
              transform: 'translate(-50%, -50%)',
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
```

---

## 4. Particle Systems

### A: Floating particles (SVG, no deps)
```tsx
const NUM_PARTICLES = 40;

// Generate deterministic particles (no Math.random — use seed)
import { random } from 'remotion';

const particles = new Array(NUM_PARTICLES).fill(0).map((_, i) => ({
  x: random(`x-${i}`) * 1920,
  y: random(`y-${i}`) * 1080,
  size: 2 + random(`s-${i}`) * 4,
  speedX: (random(`sx-${i}`) - 0.5) * 2,
  speedY: (random(`sy-${i}`) - 0.5) * 1.5,
  opacity: 0.2 + random(`o-${i}`) * 0.5,
}));

const FloatingParticles: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <svg width={1920} height={1080}>
        {particles.map((p, i) => {
          const x = (p.x + p.speedX * frame) % 1920;
          const y = (p.y + p.speedY * frame) % 1080;
          return (
            <circle
              key={i}
              cx={x < 0 ? x + 1920 : x}
              cy={y < 0 ? y + 1080 : y}
              r={p.size}
              fill="white"
              opacity={p.opacity}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
```

### B: Noise-driven particle field (@remotion/noise)
```tsx
import { noise3D } from '@remotion/noise';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

const ROWS = 12;
const COLS = 18;
const OVERSCAN = 100;

const NoiseField: React.FC<{ speed?: number; maxOffset?: number }> = ({
  speed = 0.01, maxOffset = 50,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  return (
    <AbsoluteFill>
      <svg width={width} height={height}>
        {new Array(COLS).fill(0).map((_, i) =>
          new Array(ROWS).fill(0).map((__, j) => {
            const baseX = i * ((width + OVERSCAN) / COLS);
            const baseY = j * ((height + OVERSCAN) / ROWS);
            const px = i / COLS;
            const py = j / ROWS;
            const dx = noise3D('x', px, py, frame * speed) * maxOffset;
            const dy = noise3D('y', px, py, frame * speed) * maxOffset;
            const opacity = interpolate(
              noise3D('opacity', i, j, frame * speed),
              [-1, 1],
              [0.1, 0.6]
            );
            return (
              <circle
                key={`${i}-${j}`}
                cx={baseX + dx}
                cy={baseY + dy}
                r={3}
                fill="rgba(147, 197, 253, 1)"
                opacity={opacity}
              />
            );
          })
        )}
      </svg>
    </AbsoluteFill>
  );
};
```

Install: `npm i @remotion/noise`

---

## 5. Camera Effects

### A: Ken Burns zoom (slow push-in)
```tsx
const KenBurnsZoom: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.15], {
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
      {children}
    </AbsoluteFill>
  );
};
```

### B: Camera shake (noise-based)
```tsx
import { noise3D } from '@remotion/noise';

const CameraShake: React.FC<{
  children: React.ReactNode;
  intensity?: number;
  speed?: number;
}> = ({ children, intensity = 5, speed = 0.1 }) => {
  const frame = useCurrentFrame();
  const shakeX = noise3D('shakeX', 0, 0, frame * speed) * intensity;
  const shakeY = noise3D('shakeY', 0, 0, frame * speed) * intensity;
  const rotation = noise3D('shakeR', 0, 0, frame * speed) * (intensity * 0.1);

  return (
    <AbsoluteFill
      style={{
        transform: `translate(${shakeX}px, ${shakeY}px) rotate(${rotation}deg)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
```

### C: Zoom pulse (rhythmic)
```tsx
const ZoomPulse: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const zoom = interpolate(
    frame,
    [0, durationInFrames / 4, durationInFrames / 2, 3 * durationInFrames / 4, durationInFrames],
    [1, 1.05, 1, 1.05, 1],
    { extrapolateRight: 'clamp' }
  );

  return (
    <AbsoluteFill style={{ transform: `scale(${zoom})` }}>
      {children}
    </AbsoluteFill>
  );
};
```

---

## 6. Motion Blur

### Trail effect (fast-moving elements)
```tsx
import { Trail } from '@remotion/motion-blur';

<Trail layers={50} lagInFrames={0.1} trailOpacity={1}>
  <AbsoluteFill style={{ backgroundColor: 'white', justifyContent: 'center', alignItems: 'center' }}>
    <MovingElement />
  </AbsoluteFill>
</Trail>
```

### Camera motion blur (cinematic film look)
```tsx
import { CameraMotionBlur } from '@remotion/motion-blur';

<CameraMotionBlur shutterAngle={180} samples={10}>
  <AbsoluteFill>
    <YourScene />
  </AbsoluteFill>
</CameraMotionBlur>
```

Install: `npm i @remotion/motion-blur`
Note: `samples` above 10 degrades color quality. Keep 5-10.

---

## 7. Animated Underlines & Highlights

### Expanding underline
```tsx
const AnimatedUnderline: React.FC<{
  children: React.ReactNode;
  color?: string;
  delay?: number;
}> = ({ children, color = '#6366f1', delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const width = spring({
    frame, fps, delay,
    config: { mass: 0.5, damping: 15, stiffness: 120 },
  });

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      {children}
      <span
        style={{
          position: 'absolute',
          bottom: -4,
          left: 0,
          height: 4,
          borderRadius: 2,
          backgroundColor: color,
          width: `${width * 100}%`,
        }}
      />
    </span>
  );
};
```

### Highlighter pen sweep
```tsx
const HighlighterSweep: React.FC<{
  children: React.ReactNode;
  color?: string;
  delay?: number;
}> = ({ children, color = 'rgba(250, 204, 21, 0.4)', delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sweep = spring({
    frame, fps, delay,
    config: { mass: 0.8, damping: 20, stiffness: 100, overshootClamping: true },
  });

  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span
        style={{
          position: 'absolute',
          top: '10%',
          left: 0,
          height: '80%',
          backgroundColor: color,
          width: `${sweep * 100}%`,
          zIndex: -1,
          borderRadius: 4,
          transform: `rotate(-1deg)`,
        }}
      />
      {children}
    </span>
  );
};
```

---

## 8. Counter / Number Animation

```tsx
const AnimatedCounter: React.FC<{
  from?: number;
  to: number;
  prefix?: string;
  suffix?: string;
  startFrame?: number;
  durationFrames?: number;
}> = ({ from = 0, to, prefix = '', suffix = '', startFrame = 0, durationFrames = 60 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({
    frame,
    fps,
    delay: startFrame,
    durationInFrames: durationFrames,
    config: { mass: 0.8, damping: 20, stiffness: 100, overshootClamping: true },
  });
  const value = Math.round(from + (to - from) * progress);

  return (
    <span style={{ fontVariantNumeric: 'tabular-nums', fontFamily: 'monospace' }}>
      {prefix}{value.toLocaleString()}{suffix}
    </span>
  );
};

// Usage: <AnimatedCounter to={1200000} prefix="$" suffix="+" />
```

---

## 9. Glitch / Digital Distortion

```tsx
const GlitchText: React.FC<{
  children: React.ReactNode;
  intensity?: number;
}> = ({ children, intensity = 1 }) => {
  const frame = useCurrentFrame();
  // Glitch on specific frames (intermittent)
  const isGlitching = frame % 30 < 3; // glitch 3 frames every 30

  const skewX = isGlitching ? (Math.sin(frame * 50) * 10 * intensity) : 0;
  const hueRotate = isGlitching ? (frame * 40) % 360 : 0;
  const clipTop = isGlitching ? `${30 + Math.sin(frame * 7) * 20}%` : '0%';
  const clipBottom = isGlitching ? `${70 + Math.cos(frame * 11) * 20}%` : '100%';

  return (
    <div style={{ position: 'relative' }}>
      {/* Base text */}
      <div>{children}</div>

      {/* Glitch overlay - red channel */}
      {isGlitching && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 2 * intensity,
            color: 'red',
            opacity: 0.7,
            clipPath: `inset(${clipTop} 0 ${100 - parseFloat(clipBottom)}% 0)`,
            transform: `skewX(${skewX}deg)`,
            filter: `hue-rotate(${hueRotate}deg)`,
          }}
        >
          {children}
        </div>
      )}

      {/* Glitch overlay - cyan channel */}
      {isGlitching && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: -2 * intensity,
            color: 'cyan',
            opacity: 0.7,
            mixBlendMode: 'screen',
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
};
```

Also see: https://github.com/storybynumbers/remotion-glitch-effect

---

## 10. Cinematic Composition Patterns

### Layered scene structure
```tsx
const CinematicScene: React.FC = () => {
  return (
    <>
      {/* Layer 0: Animated background */}
      <MeshGradient />

      {/* Layer 1: Particle overlay */}
      <FloatingParticles />

      {/* Layer 2: Content with camera effect */}
      <KenBurnsZoom>
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          <KineticText text="YOUR MESSAGE" staggerFrames={3} />
          <AnimatedUnderline delay={30}>
            <span style={{ fontSize: 32, color: '#a5b4fc' }}>Subtitle here</span>
          </AnimatedUnderline>
        </AbsoluteFill>
      </KenBurnsZoom>

      {/* Layer 3: Vignette overlay */}
      <AbsoluteFill
        style={{
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%)',
          pointerEvents: 'none',
        }}
      />
    </>
  );
};
```

### Scene transitions with Sequence + stagger
```tsx
import { Sequence, AbsoluteFill } from 'remotion';

const MultiSceneVideo: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <>
      <Sequence from={0} durationInFrames={fps * 4}>
        <CinematicScene />
      </Sequence>
      <Sequence from={fps * 3.5} durationInFrames={fps * 4}>
        {/* 0.5s overlap for crossfade */}
        <DataScene />
      </Sequence>
      <Sequence from={fps * 7} durationInFrames={fps * 3}>
        <CTAScene />
      </Sequence>
    </>
  );
};
```

---

## 11. Pro Rendering Settings

```bash
# High quality (CRF 15 = near-lossless, lower = better)
npx remotion render src/index.ts MyComp out/video.mp4 --crf=15

# 4K upscale
npx remotion render src/index.ts MyComp out/4k.mp4 --scale=2

# ProRes for editing pipelines
npx remotion render src/index.ts MyComp out/video.mov --codec=prores
```

---

## 12. Essential Packages

| Package | Purpose | Install |
|---------|---------|---------|
| `@remotion/noise` | Perlin noise (3D/2D) for organic motion | `npm i @remotion/noise` |
| `@remotion/motion-blur` | Trail + CameraMotionBlur | `npm i @remotion/motion-blur` |
| `@remotion/paths` | SVG path animations | `npm i @remotion/paths` |
| `remotion-animate-text` | Per-char/word CSS animations | `npm i remotion-animate-text` |
| `remotion-gl-transitions` | OpenGL transition effects | `npm i remotion-gl-transitions` |
| `@remotion/three` | React Three Fiber (3D) | `npm i @remotion/three` |
| `@remotion/skia` | Skia 2D graphics | `npm i @remotion/skia` |
| `@remotion/lottie` | Lottie animation support | `npm i @remotion/lottie` |

---

## Quick Checklist: Is My Video Cinematic?

- [ ] Background is ANIMATED (gradient, particles, noise), not flat color
- [ ] Text enters with spring physics, not linear fade
- [ ] Elements are staggered (delay param), not all at once
- [ ] Vignette overlay adds depth
- [ ] Camera has subtle movement (Ken Burns or shake)
- [ ] Numbers count up, not appear
- [ ] Key words have animated underline or highlight
- [ ] Transitions overlap slightly (crossfade)
- [ ] `extrapolateRight: 'clamp'` on all interpolations
- [ ] Using `random()` from remotion, never `Math.random()`

---

## Sources

- https://www.remotion.dev/docs/spring
- https://www.remotion.dev/docs/animating-properties
- https://www.remotion.dev/docs/noise-visualization
- https://www.remotion.dev/docs/noise/noise-3d
- https://www.remotion.dev/docs/motion-blur/trail
- https://www.remotion.dev/docs/motion-blur/camera-motion-blur
- https://www.remotion.dev/docs/resources
- https://www.remotion.dev/prompts/cinematic-tech-intro
- https://www.dplooy.com/blog/claude-code-video-with-remotion-best-motion-guide-2026
- https://www.amimetic.co.uk/blog/an-introduction-to-generative-animations-with-remotion-and-solandra
- https://github.com/remotion-dev/skills/blob/main/skills/remotion/rules/text-animations.md
- https://github.com/orgs/remotion-dev/discussions/639
