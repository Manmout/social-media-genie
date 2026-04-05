# Remotion Promo Video — Full Production Skill

## When to Use
Generate a complete promo video for any project or product. Claude analyzes the codebase/website, extracts pain points and features, then produces a Remotion video with voiceover, subtitles, and background music.

## Prerequisites
- Remotion project at `C:\Users\njeng\OneDrive\Bureau\REMOTION`
- Remotion best practices skill installed (`npx @anthropic-ai/skills add remotiondev/skills`)
- ElevenLabs API key in `.env`
- FFmpeg in PATH
- Whisper (OpenAI) for timing sync
- Python 3.13

## Pipeline

### Phase 1 — Research & Script
1. **Analyze the target** — Read the codebase, visit the URL, or ingest the brief
2. **Extract** — Key pain points, features, value props, brand colors, fonts, logos
3. **Define positioning** — Target audience, tone, CTA
4. **Write script** — One sentence per scene, total 30-60 seconds
5. **Map scenes** — Each sentence → one Remotion `<Sequence>` with timing

### Phase 2 — Remotion Composition
1. **Create project** via `mcp__remotion-video__create-project` or scaffold manually
2. **Build scenes** as React components using Remotion primitives:
   - `useCurrentFrame()`, `interpolate()`, `spring()` for animation
   - `<Sequence>`, `<Series>`, `<TransitionSeries>` for timing
   - `<AbsoluteFill>`, `<Img>`, `<Video>` for layout
3. **Use calculateMetadata** for dynamic duration based on script length
4. **Register composition** in Root.tsx at 1080x1920 (Reels) or 1920x1080 (landscape)

### Phase 3 — Voice & Audio
1. **Generate voiceover** via ElevenLabs (`eleven_multilingual_v2`)
2. **Run Whisper** on the audio → SRT with timestamps
3. **Verify timing** — Compare SRT timestamps against scene boundaries
4. **Fix overlaps** — Adjust scene durations or script length until zero overlaps
5. **Add background music** — Royalty-free from Pixabay, mixed at -18dB under voice

### Phase 4 — Assembly
1. **Render** Remotion composition → raw MP4
2. **Merge** video + voiceover via FFmpeg (`-map 0:v:0 -map 1:a:0`)
3. **Mix in music** via FFmpeg (voice at full volume, music at -18dB)
4. **Burn subtitles** via FFmpeg subtitles filter
5. **Output** → `output/videos/promo_<timestamp>.mp4`

## Prompting Principles (from production experience)

### Keep prompts simple
> "The more complicated your prompts are, the worse outputs you get. Let Claude do the heavy lifting in terms of thinking."

**Good:** "Create a 10-second promo for this app showing 2 key features. Sleek 2D animations, modern SaaS coloring."
**Bad:** Three paragraphs micro-managing every animation frame.

### Iterate, don't one-shot
Expect 2-4 rounds:
1. First pass — structure and scenes
2. Second pass — visual polish (3D elements, browser mocks, transitions)
3. Third pass — voiceover timing and script fixes
4. Fourth pass — music mixing and final render

### Scene-by-scene editing
Reference scenes by number: "Scene 4 is too dark and disconnected from the brand. Replace it with a screenshot from the website with animated text on the side."

### Timing sync is critical
- Whisper checks script against scene boundaries
- If voices overlap, shorten script or extend scene duration
- Always verify after voiceover generation

## Example Invocation

```bash
# From CLI
py -3.13 cli.py reel \
  --script "Stop paying thousands for promo videos. One skill. Professional video." \
  --caption "AI-generated promo videos #remotion #claudecode" \
  --provider remotion \
  --composition PromoVideo \
  --props '{"hook":"Stop paying thousands","scenes":[...],"cta":"Install now"}'
```

## Scene Template Library

| Scene Type | Duration | Use Case |
|-----------|----------|----------|
| Hook / Title | 2-3s | Opening with brand + tagline |
| Pain Points | 3-5s | 3 bullet problems with icons |
| Feature Showcase | 4-6s | Screenshot + animated callouts |
| Stats / Social Proof | 3-4s | Big numbers with spring animations |
| Before/After | 4-6s | Split screen comparison |
| Browser Mock | 4-6s | Product UI in animated browser frame |
| CTA | 2-3s | Logo + action + URL |

## Transition Library

| Transition | Effect | Best For |
|-----------|--------|----------|
| Slide from right | Horizontal wipe | Sequential features |
| Zoom through | Scale up into next scene | Dramatic reveals |
| Metallic swoosh | Shiny horizontal sweep | Premium feel |
| Fade + scale | Opacity + slight zoom | Calm, professional |
| Speed blur | Motion blur flash | Energy, urgency |
