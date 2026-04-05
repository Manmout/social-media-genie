# Remotion Iterate & Chain — Editing and Multi-Video Skill

## When to Use
- Refine a Remotion video through iterative prompts (scene edits, timing fixes, style changes)
- Chain multiple videos into one end-to-end production
- Fix common issues: robotic voice, overlapping audio, wrong timing, dark scenes

## Part 1 — Iterative Editing

### The Iteration Loop
Expect 2-4 rounds to get a polished video. Each round targets one layer:

```
Round 1: Structure  → Are the scenes right? Is the story arc correct?
Round 2: Visuals    → Colors, animations, brand assets, screenshots
Round 3: Audio      → Voiceover quality, timing sync, music balance
Round 4: Polish     → Transitions, final timing, subtitle styling
```

### How to Give Feedback

**Be specific about WHAT and WHERE:**
- "Scene 4 is too dark and feels disconnected from the brand"
- "The title font is too small — make it 120px"
- "Voice and text overlap from scene 4 onward"

**Don't micro-manage HOW:**
- Bad: "Change the interpolate function on line 47 to use a spring with damping 0.8"
- Good: "Make the text entrance bouncier"

**Reference scenes by number or description:**
- "The pain points scene" or "Scene 2"
- "The CTA at the end" or "The last scene"

### Common Fixes

| Problem | Prompt |
|---------|--------|
| Robotic voiceover | "The voice sounds robotic. Use a more natural ElevenLabs voice — try 'Matilda' or 'Antoni'" |
| Audio overlapping | "Voices overlap from scene 4. Check script length vs scene duration and fix timing" |
| Scene too dark | "Scene 3 is too dark. Use the brand's light theme with white background" |
| Text too small | "All title text should be much bigger — at least 96px" |
| Missing brand feel | "Pull colors and fonts from the website. Use their actual logo" |
| Animation too fast | "Slow down the transitions. Each scene needs at least 3 seconds" |
| Wrong aspect ratio | "This needs to be 9:16 for Instagram Reels, not 16:9" |

### Website-to-Video Workflow
Claude can analyze a URL and extract brand assets:
1. Visit URL, take screenshots
2. Extract: logo, brand colors, fonts, key UI screenshots
3. Use extracted assets in Remotion scenes
4. No manual design work needed

Prompt: "Go to [URL], take screenshots, extract the logo and brand colors, then create a 15-second product demo using their actual design language."

## Part 2 — Video Chaining

### Concept
Produce multiple video segments independently, then chain them into one final video.

```
Video 1 (Intro)  ─┐
Video 2 (Body)   ─┼──→ FFmpeg concat ──→ Final Video
Video 3 (Outro)  ─┘
```

### When to Chain
- Intro + main content + CTA (different styles per section)
- Multi-product showcase (one segment per product)
- Story arc with distinct chapters
- Mixing Remotion (template scenes) + Runway (cinematic B-roll)

### How to Chain

#### Option A — FFmpeg concat (different source files)
```python
from src.utils.ffmpeg import concat_clips
from pathlib import Path

clips = [
    Path("output/videos/intro.mp4"),
    Path("output/videos/main.mp4"),
    Path("output/videos/cta.mp4"),
]
await concat_clips(clips, Path("output/videos/final_chained.mp4"))
```

#### Option B — Remotion Series (same composition)
Build all segments as `<Sequence>` blocks inside one composition:
```tsx
<Series>
  <Series.Sequence durationInFrames={90}><IntroScene /></Series.Sequence>
  <Series.Sequence durationInFrames={300}><MainContent /></Series.Sequence>
  <Series.Sequence durationInFrames={75}><CTAScene /></Series.Sequence>
</Series>
```

#### Option C — Prompt Claude
"Chain video_intro.mp4, video_features.mp4, and video_cta.mp4 into one final video with smooth transitions between them."

### Audio Mixing for Chained Videos

When chaining segments with different audio tracks:
1. Render each segment as video-only (no audio)
2. Generate one continuous voiceover for the full script
3. Generate or select one background music track
4. Merge: `video + voiceover + music` in one FFmpeg pass

```bash
ffmpeg -y \
  -i chained_video.mp4 \
  -i full_voiceover.mp3 \
  -i background_music.mp3 \
  -filter_complex "[1:a]volume=1.0[voice];[2:a]volume=0.15[music];[voice][music]amix=inputs=2:duration=first[aout]" \
  -map 0:v:0 -map "[aout]" \
  -c:v copy -c:a aac \
  final_with_audio.mp4
```

## Part 3 — Quality Checklist

Before declaring a video done:

- [ ] Aspect ratio correct (1080x1920 for Reels, 1920x1080 for YouTube)
- [ ] All text readable (min 48px for body, 72px+ for titles on mobile)
- [ ] No audio overlap between scenes
- [ ] Voiceover sounds natural (not robotic)
- [ ] Background music audible but not overpowering (–15 to –18dB)
- [ ] Subtitles present and correctly timed
- [ ] CTA is clear and visible for at least 2 seconds
- [ ] Brand colors/logo consistent throughout
- [ ] Total duration within platform limits (90s for Reels, 60s for TikTok)
- [ ] File size reasonable (< 100MB for Instagram upload)
