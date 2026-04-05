# Remotion Agent Skills — Setup & Architecture

## When to Use
Setting up Remotion with Claude Code for the first time, or explaining the architecture to collaborators.

## What Are Remotion Agent Skills?
A "skill" is a structured instruction set that tells Claude how to use Remotion correctly. Think of Claude as a chef — the skill is the recipe. Without it, Claude can write React code, but won't know Remotion's specific APIs, best practices, or rendering pipeline.

## Installation

### 1. Install Remotion Best Practices Skill
```bash
npx @anthropic-ai/skills add remotiondev/skills
```
This gives Claude Code knowledge of:
- Remotion component patterns (`useCurrentFrame`, `interpolate`, `spring`)
- Composition registration and `calculateMetadata`
- Rendering pipeline (`npx remotion render`)
- Best practices (deterministic code, no `Math.random()`, frame-based animation)

### 2. Verify Installation
In Claude Code, check that the skill is loaded:
```
/skills
```
Should show `remotion-best-practices` in the list.

### 3. Project Structure
Our Remotion project lives at `C:\Users\njeng\OneDrive\Bureau\REMOTION`:

```
src/
  Root.tsx              — Composition registry
  MyComp.tsx            — Default demo composition
  GorgusNuit.tsx        — GorgusWorld night scene (59s)
  HemleTrailer.tsx      — Hemle Publishing trailer (26s)
  reels/
    KineticText.tsx     — Hook → facts → CTA (dynamic duration)
    QuoteCard.tsx       — Quote + author + CTA
    Listicle.tsx        — Title → numbered items
    BeforeAfter.tsx     — Before/After comparison
    shared.tsx          — Shared palettes, fonts, animations
    index.ts            — Barrel export
public/                 — Static assets (images, fonts, audio)
out/                    — Rendered videos
```

### 4. Integration with Social Media Genie
The `RemotionClient` in `src/apis/remotion.py` bridges Python → Remotion:

```
CLI (cli.py)
  → Pipeline (pipeline.py)
    → RemotionClient.render(composition_id, output_path, props)
      → npx remotion render <comp> <output> --props <file>
```

Props are serialized to a temp JSON file (Windows shell can't handle inline JSON).

## MCP Tools Available

If using Remotion MCP server:
- `mcp__remotion-video__create-project` — Scaffold new Remotion project
- `mcp__remotion-video__edit-project` — Modify existing project
- `mcp__remotion-video__launch-studio` — Open Remotion Studio (visual preview)
- `mcp__remotion-video__get-project-info` — List compositions and metadata
- `mcp__remotion-video__generate-audio` — Generate audio tracks
- `mcp__remotion-video__configure-audio` — Set audio mixing parameters

## Key Remotion Patterns

### Frame-Based Animation
```tsx
const frame = useCurrentFrame();
const opacity = interpolate(frame, [0, 30], [0, 1], {
  extrapolateRight: 'clamp',
});
```

### Spring Animation
```tsx
const scale = spring({
  frame,
  fps: 30,
  config: { damping: 12, mass: 0.5 },
});
```

### Sequencing
```tsx
<Series>
  <Series.Sequence durationInFrames={90}><Scene1 /></Series.Sequence>
  <Series.Sequence durationInFrames={120}><Scene2 /></Series.Sequence>
</Series>
```

### Dynamic Duration
```tsx
<Composition
  id="MyReel"
  component={MyReel}
  calculateMetadata={({props}) => ({
    durationInFrames: calculateDuration(props),
    width: 1080,
    height: 1920,
    fps: 30,
  })}
  defaultProps={defaults}
/>
```

### Determinism Rule
All Remotion code MUST be deterministic:
- Use `random(seed)` from `remotion`, never `Math.random()`
- No `Date.now()` in render logic
- No network requests during render
- Same frame number must always produce same visual output

## Rendering

### Local Render
```bash
npx remotion render KineticText output/reel.mp4 --width 1080 --height 1920
```

### With Custom Props
```bash
npx remotion render KineticText output/reel.mp4 --props props.json
```

### Studio Preview (visual editor)
```bash
npx remotion studio
```
Opens browser at `localhost:3000` with real-time preview, timeline, and prop editor.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Version mismatch warnings | Non-fatal — video still renders. Run `npm update` to silence. |
| Props JSON mangled on Windows | Already fixed — props written to temp file, not inline |
| Paths with spaces fail | Already fixed — `subprocess.list2cmdline()` quotes properly |
| Render produces no file | Check Remotion Studio first — composition may have a React error |
| Audio missing from final | Remotion embeds silent audio track — use `-map 0:v:0 -map 1:a:0` in FFmpeg merge |
