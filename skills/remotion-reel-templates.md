# Remotion Reel Templates — Composition Skill

## When to Use
Pick the right Remotion composition for each content type. Pass custom props via `--props` JSON to customize without touching React code.

## Available Compositions (9:16, 1080x1920)

### KineticText
Animated hook → facts cascade → CTA. Best for educational/stat content.

```json
{
  "hook": "Wild Gorilla Fact",
  "facts": [
    "Baby gorillas laugh when tickled",
    "They share 98% of our DNA",
    "They make play sounds during games"
  ],
  "cta": "Follow for more",
  "palette": "dark",
  "handle": "@gorgusworld"
}
```

**Duration:** `60 + facts.length * 75 + 75` frames (hook + facts + cta)
**Palettes:** `dark`, `light`, `ocean`, `warm`, `mint`

### QuoteCard
Single quote with author attribution + optional CTA. Best for thought leadership.

```json
{
  "quote": "The best marketing doesn't feel like marketing",
  "author": "Tom Fishburne",
  "emoji": "lightbulb",
  "cta": "Save this for later",
  "palette": "ocean",
  "handle": "@gorgusworld"
}
```

**Duration:** `max(150, 60 + wordCount * 6) + (cta ? 75 : 0)` frames

### Listicle
Numbered items with emojis. Best for tool lists, tips, resources.

```json
{
  "title": "5 gorilla facts you didn't know",
  "items": [
    {"text": "They live in family groups of 5-30", "emoji": "family"},
    {"text": "Silverbacks can weigh 200kg", "emoji": "muscle"},
    {"text": "They build new nests every night", "emoji": "house"},
    {"text": "They share 98% of human DNA", "emoji": "dna"},
    {"text": "Baby gorillas laugh when tickled", "emoji": "joy"}
  ],
  "cta": "Follow @gorgusworld",
  "palette": "warm",
  "handle": "@gorgusworld"
}
```

**Duration:** `60 + items.length * 75 + 75` frames

### BeforeAfter
Split comparison with dramatic flash transition. Best for transformations.

```json
{
  "hook": "Stop doing this",
  "before": {
    "label": "Before",
    "points": ["Manual posting every day", "Zero engagement strategy", "No analytics"]
  },
  "after": {
    "label": "After",
    "points": ["AI-generated Reels in 2 min", "Auto-DMs with 90% open rate", "Full pipeline analytics"]
  },
  "cta": "Try Social Media Genie",
  "palette": "mint",
  "handle": "@gorgusworld"
}
```

**Duration:** 390 frames fixed (13 seconds)

## CLI Quick Reference

```bash
# KineticText
py -3.13 cli.py reel --script "VOICEOVER" --caption "CAPTION" --provider remotion --composition KineticText --props "{...}"

# QuoteCard
py -3.13 cli.py reel --script "VOICEOVER" --caption "CAPTION" --provider remotion --composition QuoteCard --props "{...}"

# Listicle
py -3.13 cli.py reel --script "VOICEOVER" --caption "CAPTION" --provider remotion --composition Listicle --props "{...}"

# BeforeAfter
py -3.13 cli.py reel --script "VOICEOVER" --caption "CAPTION" --provider remotion --composition BeforeAfter --props "{...}"
```

## Content-to-Template Mapping

| Content Type | Best Template | Why |
|-------------|--------------|-----|
| Stats / Did you know | KineticText | Facts cascade with punch |
| Inspirational / Wisdom | QuoteCard | Clean, shareable, saveable |
| Tool lists / Tips | Listicle | Numbered, scannable |
| Transformation / Results | BeforeAfter | Dramatic contrast |
| Product demo | Custom composition | Needs screenshots + UI mocks |
| Testimonial | QuoteCard (adapted) | Author = customer name |

## Creating New Compositions

When existing templates don't fit, create a new one:

1. Create `src/reels/NewTemplate.tsx` exporting component + props type
2. Use `useCurrentFrame()` + `interpolate()` for all animations
3. Use shared palette system from `src/reels/shared.tsx`
4. Register in `src/Root.tsx` with `calculateMetadata` for dynamic duration
5. All code must be deterministic — use `random()` from remotion, never `Math.random()`

## GorgusWorld Brand Defaults

For all @gorgusworld content, use these defaults:
- `handle`: `"@gorgusworld"`
- `palette`: `"dark"` or `"warm"` (forest/nature feel)
- Voiceover language: `"fr"` (French) or `"en"` (English)
- Themes: wildlife facts, conservation, African fauna, infant gorilla adventures
