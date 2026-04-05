---
name: artclic-web-builder
description: >
  Complete web building system for Artclic Studios / hemle.blog properties. Use this skill
  whenever the user asks to build, design, or scaffold ANY website, page, or UI component
  related to: hemle.blog, Social Media Genie, pipeline dashboards, logbooks, landing pages,
  editorial blogs, admin interfaces, or any Artclic Studios project. Also trigger for general
  site requests when the user wants a consistent visual identity applied. This skill defines
  the canonical Artclic visual DNA, file architecture, tech stack, and UX patterns — always
  consult it before writing a single line of HTML/CSS/JS for these properties.
---

# Artclic Web Builder

Système complet de construction de sites pour l'écosystème **Artclic Studios** / **hemle.blog**.
Ce skill couvre 4 types de sites distincts, tous partageant une identité visuelle commune.

---

## 1. Identité Visuelle Canonique (PRIORITÉ ABSOLUE)

Appliquer ces tokens à **tous** les sites sans exception.

### Palette

```css
:root {
  /* Backgrounds */
  --bg-hero:     #0d0618;   /* Dark purple — hero sections, headers */
  --bg-deep:     #1a0a2e;   /* Deeper purple — sections alternées */
  --bg-surface:  #ede8f8;   /* Lavande clair — cards, surfaces éditorials */
  --bg-page:     #f7f5fb;   /* Off-white violet — fond de page clair */

  /* Accent */
  --accent:      #6b3fc0;   /* Violet principal */
  --accent-light:#8b5cf6;   /* Violet hover / highlight */
  --accent-glow: rgba(107, 63, 192, 0.25); /* Pour box-shadow et glows */

  /* Texte */
  --text-on-dark:  #f0ebfc;
  --text-on-light: #1a0a2e;
  --text-muted:    #8875a8;

  /* Borders */
  --border-subtle: rgba(107, 63, 192, 0.18);
  --border-active: rgba(107, 63, 192, 0.55);
}
```

### Typographie

```css
/* Éditorial / corps de texte */
body, .editorial { font-family: Georgia, 'Times New Roman', serif; }

/* UI / labels / navigation */
.ui, nav, label, button, .meta { font-family: system-ui, -apple-system, sans-serif; }

/* Règles invariables */
p, .body-text    { text-align: justify; line-height: 1.75; }
h1               { font-size: clamp(2rem, 5vw, 3.5rem); font-weight: 700; }
h2               { font-size: clamp(1.4rem, 3vw, 2.2rem); font-weight: 600; }
.meta, .label    { font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
```

### Effets Signature

```css
/* Card standard */
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  padding: 1.5rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.card:hover {
  border-color: var(--border-active);
  box-shadow: 0 4px 24px var(--accent-glow);
}

/* Hero gradient overlay */
.hero {
  background: linear-gradient(135deg, var(--bg-hero) 0%, var(--bg-deep) 100%);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 30% 50%, var(--accent-glow) 0%, transparent 65%);
  pointer-events: none;
}

/* Accent bar sur titres */
.section-title::after {
  content: '';
  display: block;
  width: 40px;
  height: 3px;
  background: var(--accent);
  margin-top: 0.5rem;
}
```

---

## 2. Architecture Fichiers par Type de Site

Consulte le fichier de référence approprié selon le type demandé :

| Type de site | Fichier de référence |
|---|---|
| Landing page / vitrine | `references/landing.md` |
| Blog / éditorial (hemle.blog) | `references/blog.md` |
| Dashboard / admin (pipeline) | `references/dashboard.md` |
| Pipeline docs / logbook | `references/logbook.md` |

**Toujours lire le fichier de référence avant de coder.**

---

## 3. Stack Technique Canonique

### HTML/CSS Vanilla (défaut pour landing pages, logbooks)
- Pas de framework — HTML sémantique + CSS custom properties
- Un seul fichier `index.html` si livrable artifact Claude.ai
- Fichiers séparés `style.css` + `main.js` si projet Claude Code

### React (dashboards, apps interactives)
- Vite + React 18
- Tailwind CSS **uniquement pour les utilitaires** — design tokens via CSS variables
- Structure : `src/components/`, `src/pages/`, `src/hooks/`
- Lucide React pour les icônes

### WordPress (hemle.blog)
- Thème enfant sur base Blocksy ou GeneratePress
- CSS injecté via `Additional CSS` ou `functions.php`
- Pas de page builders — blocs Gutenberg natifs

### Règles transverses
- Mobile-first, breakpoints : `640px`, `1024px`, `1280px`
- Jamais de polices génériques (Inter, Roboto, Arial) sur les titres
- Images : `aspect-ratio` fixé, `object-fit: cover`, lazy loading natif
- Accessibilité : `aria-label` sur tous les boutons icon-only, contraste AA minimum

---

## 4. Patterns UX Clés

### Navigation
```html
<!-- Pattern nav sombre sur hero -->
<nav class="nav-dark">
  <a class="nav-brand" href="/">hemle</a>
  <ul class="nav-links"><!-- items --></ul>
  <button class="nav-cta">S'abonner</button>
</nav>
```

### CTA primaire
```html
<a class="btn-primary" href="#">
  <span>Lire l'article</span>
  <svg><!-- arrow icon --></svg>
</a>
```
```css
.btn-primary {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: var(--accent); color: #fff;
  padding: 0.75rem 1.5rem; border-radius: 8px;
  font-family: system-ui; font-weight: 600;
  transition: background 0.15s, transform 0.1s;
}
.btn-primary:hover { background: var(--accent-light); transform: translateY(-1px); }
```

### Badges / Tags éditoriaux
```html
<span class="tag">IA Générative</span>
```
```css
.tag {
  background: var(--accent-glow); color: var(--accent-light);
  border: 1px solid var(--border-active);
  padding: 0.2rem 0.65rem; border-radius: 20px;
  font-family: system-ui; font-size: 0.75rem; font-weight: 600;
}
```

---

## 5. Workflow de Construction

```
1. Identifier le type de site → lire le fichier references/ correspondant
2. Appliquer les tokens CSS de la section 1 en premier
3. Structurer l'architecture fichiers (section 2)
4. Choisir le stack (section 3)
5. Implémenter les patterns UX (section 4)
6. Vérifier : mobile-first ✓ | justify sur body ✓ | Georgia sur éditorial ✓ | accent #6b3fc0 ✓
```

---

## Points de Vigilance

- **Ne jamais mélanger** l'API WordPress.com v1.1 et `/wp-json/wp/v2/` — ce sont deux systèmes distincts
- **Tumblr** : NPF JSON blocks uniquement, pas de HTML brut
- Le dashboard Google Sheets utilise `.dashboard_config.json` pour stocker le `spreadsheetId`
- Les `gws` calls doivent être wrappés en try/except avec silent failure logging
