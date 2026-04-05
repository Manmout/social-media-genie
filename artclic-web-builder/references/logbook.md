# Pipeline Docs / Logbook — Référence

## Contexte
Le **logbook** est la vitrine de la transparence du pipeline Social Media Genie.
Il documente les décisions créatives de l'IA : trend scoring, angles rejetés, choix éditoriaux.
Publié automatiquement via `logbook_publisher.py` → catégorie `behind-the-machine` sur hemle.blog.

Deux faces du logbook :
1. **Vue WordPress** — Posts publics dans "Behind the Machine"
2. **Vue dashboard interne** — Détail JSON brut + timeline par run_id

## Structure d'un Post Logbook (WordPress)

```
Titre   : [RUN-xxx] Logbook — {subject} — {date}
Catégorie: behind-the-machine
Statut  : publish (public, indexable)

Corps HTML :
├── .logbook-meta        run_id + timestamp + trend_score
├── .logbook-section     "Angles analysés" (tableau)
├── .logbook-section     "Angle retenu" (highlight)
├── .logbook-section     "Décision éditoriale" (corps justify Georgia)
├── .logbook-section     "Publications générées" (liens platform)
└── .logbook-footer      "Généré automatiquement par Social Media Genie"
```

## Template HTML Logbook Post

```html
<div class="logbook-post">

  <!-- Meta header -->
  <div class="logbook-meta">
    <span class="meta">RUN-{run_id}</span>
    <span class="meta">{timestamp}</span>
    <span class="tag">Trend Score: {trend_score}/100</span>
  </div>

  <!-- Angles analysés -->
  <div class="logbook-section">
    <h3 class="section-title">Angles analysés</h3>
    <table class="angles-table">
      <thead><tr><th>Angle</th><th>Score</th><th>Statut</th></tr></thead>
      <tbody>
        <!-- généré dynamiquement -->
      </tbody>
    </table>
  </div>

  <!-- Angle retenu -->
  <div class="logbook-highlight">
    <span class="meta">Angle retenu</span>
    <p class="highlight-text">{angle_retenu}</p>
  </div>

  <!-- Décision éditoriale -->
  <div class="logbook-section">
    <h3 class="section-title">Raisonnement éditorial</h3>
    <div class="editorial-body">{chain_of_thought}</div>
  </div>

  <!-- Publications -->
  <div class="logbook-section">
    <h3 class="section-title">Publications générées</h3>
    <div class="publication-links">
      <a class="pub-link" href="{url_wordpress}">hemle.blog →</a>
      <a class="pub-link" href="{url_tumblr}">Tumblr →</a>
      <a class="pub-link" href="{url_newsletter}">Newsletter →</a>
    </div>
  </div>

  <!-- Footer auto -->
  <footer class="logbook-footer">
    <span>Généré automatiquement par <strong>Social Media Genie</strong></span>
    <span class="meta">Artclic Studios · {year}</span>
  </footer>

</div>
```

## CSS Logbook

```css
.logbook-post {
  max-width: 760px;
  margin: 0 auto;
  font-family: Georgia, serif;
}

.logbook-meta {
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
  padding: 1rem;
  background: var(--bg-surface);
  border-left: 4px solid var(--accent);
  border-radius: 0 8px 8px 0;
  margin-bottom: 2rem;
}

.logbook-section { margin: 2rem 0; }
.logbook-section .section-title { font-family: system-ui; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); margin-bottom: 1rem; }

.logbook-highlight {
  background: linear-gradient(135deg, var(--bg-deep), #2a1050);
  color: var(--text-on-dark);
  padding: 1.5rem;
  border-radius: 12px;
  margin: 2rem 0;
}
.logbook-highlight .highlight-text { font-size: 1.15rem; font-style: italic; margin: 0.5rem 0 0; }

.angles-table { width: 100%; border-collapse: collapse; font-family: system-ui; font-size: 0.875rem; }
.angles-table th { background: var(--bg-surface); color: var(--text-muted); text-align: left; padding: 0.5rem 1rem; border-bottom: 1px solid var(--border-subtle); }
.angles-table td { padding: 0.6rem 1rem; border-bottom: 1px solid var(--border-subtle); }
.angles-table tr:last-child td { border-bottom: none; }

.editorial-body { font-size: 1.05rem; line-height: 1.8; text-align: justify; color: var(--text-on-light); }

.publication-links { display: flex; gap: 1rem; flex-wrap: wrap; }
.pub-link {
  display: inline-flex; align-items: center; gap: 0.4rem;
  padding: 0.5rem 1rem;
  background: var(--accent-glow); color: var(--accent-light);
  border: 1px solid var(--border-active);
  border-radius: 8px; font-family: system-ui; font-size: 0.875rem; font-weight: 600;
  text-decoration: none; transition: background 0.15s;
}
.pub-link:hover { background: rgba(107, 63, 192, 0.35); }

.logbook-footer {
  display: flex; justify-content: space-between; align-items: center;
  padding-top: 2rem;
  border-top: 1px solid var(--border-subtle);
  font-family: system-ui; font-size: 0.8rem; color: var(--text-muted);
  margin-top: 3rem;
}
```

## logbook_publisher.py — Données Attendues

```python
# Structure JSON envoyée au publisher
logbook_data = {
    "run_id":          "abc123",
    "timestamp":       "2026-04-01T14:30:00Z",
    "subject":         "L'IA dans la création musicale",
    "trend_score":     87,
    "angles_analyzed": [
        {"angle": "Impact sur les musiciens indépendants", "score": 87, "status": "retenu"},
        {"angle": "Outils IA vs DAW traditionnels",        "score": 72, "status": "rejeté"},
        {"angle": "Aspect légal des droits d'auteur IA",   "score": 65, "status": "rejeté"},
    ],
    "angle_retenu":    "Impact sur les musiciens indépendants",
    "chain_of_thought":"L'angle économique et humain génère plus d'engagement...",
    "url_wordpress":   "https://hemle.blog/...",
    "url_tumblr":      "https://hemle.tumblr.com/...",
    "url_newsletter":  "https://...",
}
```

## Page Logbook Archive (Standalone HTML)

Pour une page d'archive des logbooks indépendante de WordPress :

```
index.html
├── Header dark           "Behind the Machine" + description
├── Filters bar           Filtre par trend_score / date / platform
├── Timeline              Liste chronologique de runs
│   └── RunCard           run_id + subject + score + 4 pub links
└── Stats sidebar         Total runs / Avg trend score / Publications
```

## Checklist Livraison
- [ ] `run_id` toujours affiché en monospace
- [ ] Tableau angles : ligne "retenu" surlignée en accent-glow
- [ ] `chain_of_thought` en italic Georgia avec text-align: justify
- [ ] Liens publications s'ouvrent en `target="_blank" rel="noopener"`
- [ ] Footer mentionne "Social Media Genie" et "Artclic Studios"
- [ ] Catégorie WordPress `behind-the-machine` (slug exact, pas d'espaces)
