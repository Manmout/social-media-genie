# Landing Page / Vitrine — Référence

## Structure HTML

```
index.html
├── <nav>          Navigation fixe, fond transparent → opaque au scroll
├── <section.hero> Dark bg-hero, headline + subline + CTA
├── <section.features> Cards sur bg-page
├── <section.social-proof> Testimonials ou stats sur bg-deep (dark)
├── <section.cta-band> Bande accent pleine largeur
└── <footer>       Dark bg-hero
```

## Sections Canoniques

### Hero
- Background : `var(--bg-hero)` + effet radial gradient (voir SKILL.md section 1)
- Headline : Georgia, `clamp(2.5rem, 6vw, 4rem)`, couleur `var(--text-on-dark)`
- Subline : system-ui, `1.1rem`, `var(--text-muted)`, max-width 560px, centré
- CTA principal : `btn-primary` + CTA secondaire ghost (border: 1px solid var(--border-active))
- Optionnel : floating badge "Propulsé par IA" en haut à droite

### Features Grid
```css
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}
```
Chaque card = icône Lucide + titre + description justify.

### Social Proof (sur fond dark)
- Fond : `var(--bg-deep)`
- Stats : grands chiffres Georgia + label system-ui muted
- Layout : flexbox centré, gap 3rem

### CTA Band
```css
.cta-band {
  background: linear-gradient(90deg, var(--accent) 0%, var(--accent-light) 100%);
  padding: 4rem 2rem;
  text-align: center;
}
```

## Navigation au Scroll
```js
window.addEventListener('scroll', () => {
  const nav = document.querySelector('nav');
  nav.classList.toggle('scrolled', window.scrollY > 60);
});
```
```css
nav { transition: background 0.3s; }
nav.scrolled { background: rgba(13, 6, 24, 0.95); backdrop-filter: blur(12px); }
```

## Checklist Livraison
- [ ] Meta OG tags (title, description, image)
- [ ] Font preconnect Google Fonts si utilisé
- [ ] `loading="lazy"` sur toutes les images
- [ ] `aria-label` sur nav burger mobile
- [ ] Section hero en `min-height: 100svh`
