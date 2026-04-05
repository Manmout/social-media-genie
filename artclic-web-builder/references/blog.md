# Blog / Éditorial hemle.blog — Référence

## Contexte
Site principal : hemle.blog (WordPress.com, API v1.1)
Newsletters : FR + EN via Brevo (hello@hemle.blog, DKIM + DMARC configurés)
Positionnement : "Autonomous Creative Agency" — IA éditoriale haute autonomie

## Structure Page

```
├── Header sticky       Logo + nav catégories + bouton newsletter
├── Hero article        Grande image + category tag + titre + meta
├── Body éditorial      2 colonnes max 720px + sidebar 280px
│   ├── Article text    Georgia, justify, line-height 1.75
│   ├── Pull quotes     Accent left-border violet
│   ├── Code blocks     Dark bg-deep, monospace
│   └── Sidebar         Tags / Articles liés / CTA newsletter
└── Footer              Dark + liens réseaux + mention "Propulsé par IA"
```

## Typographie Éditorial

```css
/* Article body */
.article-body {
  font-family: Georgia, serif;
  font-size: 1.125rem;
  line-height: 1.85;
  color: var(--text-on-light);
  text-align: justify;
  max-width: 680px;
}

/* Pull quote */
.pull-quote {
  border-left: 4px solid var(--accent);
  padding: 1rem 1.5rem;
  margin: 2rem 0;
  font-size: 1.25rem;
  font-style: italic;
  color: var(--accent);
  background: var(--bg-surface);
  border-radius: 0 8px 8px 0;
}

/* Chapô / intro */
.article-intro {
  font-size: 1.2rem;
  font-weight: 500;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}
```

## Card Article (liste / archive)

```html
<article class="article-card">
  <div class="card-img-wrap">
    <img src="..." alt="..." loading="lazy">
    <span class="tag">IA Générative</span>
  </div>
  <div class="card-body">
    <time class="meta">12 mars 2026</time>
    <h2 class="card-title">Titre de l'article</h2>
    <p class="card-excerpt">Extrait justify...</p>
    <a class="btn-primary" href="#">Lire →</a>
  </div>
</article>
```

```css
.article-card .card-img-wrap { position: relative; aspect-ratio: 16/9; overflow: hidden; border-radius: 12px 12px 0 0; }
.article-card .card-img-wrap .tag { position: absolute; top: 1rem; left: 1rem; }
.article-card { background: var(--bg-surface); border-radius: 12px; overflow: hidden; border: 1px solid var(--border-subtle); }
```

## Newsletter Embed (Brevo)

```html
<!-- Inline newsletter CTA — style hemle -->
<div class="newsletter-embed">
  <p class="meta">La Lettre hemle</p>
  <h3>Chaque semaine, l'IA décryptée.</h3>
  <form class="newsletter-form">
    <input type="email" placeholder="votre@email.com" aria-label="Adresse email">
    <button type="submit" class="btn-primary">S'abonner</button>
  </form>
</div>
```

## Catégories hemle.blog

- `ia-generative` — articles IA générale
- `behind-the-machine` — logbook pipeline (catégorie auto-générée)
- `interviews-with-agents` — série éditoriale NotebookLM
- `analyse` — décryptages longs formats
- `outils` — reviews outils IA

## WordPress Specific

```php
// functions.php — Couleurs éditorial dans theme.json ou Additional CSS
// JAMAIS de custom post types via plugins — utiliser les catégories natives
// Images : taille recommandée hero 1440×810, card 800×450
```

## Checklist Livraison
- [ ] Schema Article JSON-LD (headline, datePublished, author)
- [ ] Open Graph + Twitter Card
- [ ] Canonical URL sur chaque post
- [ ] `alt` text sur toutes les images
- [ ] Catégorie `behind-the-machine` liée au logbook_publisher.py
