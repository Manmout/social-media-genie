# Dashboard / Admin Pipeline — Référence

## Contexte
Dashboard principal : monitoring de Social Media Genie
Stack : React + Vite + Tailwind (utilitaires) + CSS variables Artclic
Données : Google Sheets (spreadsheetId dans `.dashboard_config.json`)

## Structure App React

```
src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx        Navigation verticale dark
│   │   ├── TopBar.jsx         Run ID actif + status + actions rapides
│   │   └── Layout.jsx         Wrapper global
│   ├── ui/
│   │   ├── StatCard.jsx       Carte métrique (chiffre + label + trend)
│   │   ├── StatusBadge.jsx    Pill coloré (running/success/error/pending)
│   │   ├── RunTimeline.jsx    Timeline d'un run complet
│   │   └── PublicationGrid.jsx URLs publiées par plateforme
│   └── pages/
│       ├── DashboardHome.jsx  Vue d'ensemble + derniers runs
│       ├── RunDetail.jsx      Détail d'un run_id
│       ├── LogbookView.jsx    Posts behind-the-machine
│       └── Settings.jsx       Config pipeline
├── hooks/
│   ├── useSheetData.js        Polling Sheets API
│   └── usePipelineStatus.js   Status run en cours
└── lib/
    └── sheetsClient.js        Wrapper gws / API Sheets
```

## Layout Dark Sidebar

```css
.sidebar {
  width: 240px;
  background: var(--bg-hero);
  border-right: 1px solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  padding: 1.5rem 1rem;
  gap: 0.5rem;
}

.sidebar-item {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.65rem 1rem;
  border-radius: 8px;
  color: var(--text-muted);
  font-family: system-ui; font-size: 0.875rem;
  transition: background 0.15s, color 0.15s;
  cursor: pointer;
}
.sidebar-item:hover, .sidebar-item.active {
  background: rgba(107, 63, 192, 0.15);
  color: var(--text-on-dark);
}
.sidebar-item.active { border-left: 3px solid var(--accent); }
```

## StatCard Component

```jsx
// StatCard.jsx
export function StatCard({ label, value, trend, icon: Icon }) {
  return (
    <div className="stat-card">
      <div className="stat-header">
        <span className="stat-label">{label}</span>
        {Icon && <Icon size={16} className="stat-icon" />}
      </div>
      <div className="stat-value">{value}</div>
      {trend && <div className={`stat-trend ${trend > 0 ? 'up' : 'down'}`}>
        {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}%
      </div>}
    </div>
  );
}
```

```css
.stat-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px; padding: 1.25rem;
}
.stat-label { font-family: system-ui; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted); }
.stat-value { font-family: Georgia; font-size: 2rem; font-weight: 700; color: var(--text-on-light); margin: 0.5rem 0; }
.stat-trend.up { color: #22c55e; font-size: 0.8rem; }
.stat-trend.down { color: #ef4444; font-size: 0.8rem; }
```

## StatusBadge

```jsx
const STATUS_CONFIG = {
  running:  { label: 'En cours',  bg: 'rgba(234,179,8,0.15)',   color: '#eab308' },
  success:  { label: 'Publié',    bg: 'rgba(34,197,94,0.15)',   color: '#22c55e' },
  error:    { label: 'Erreur',    bg: 'rgba(239,68,68,0.15)',   color: '#ef4444' },
  pending:  { label: 'En attente',bg: 'rgba(107,63,192,0.15)',  color: '#8b5cf6' },
};
```

## Google Sheets — Schema Colonnes

```js
// Colonnes du dashboard Google Sheets (sheets_dashboard.py)
const COLUMNS = [
  'run_id',        // A — UUID unique du run
  'timestamp',     // B — ISO 8601
  'subject',       // C — Sujet traité
  'trend_score',   // D — Score 0-100
  'angle_retenu',  // E — Angle éditorial choisi
  'url_wordpress', // F — URL hemle.blog
  'url_tumblr',    // G — URL Tumblr principal
  'url_newsletter',// H — URL campagne Brevo
  'url_logbook',   // I — URL post logbook
  'podcast_status',// J — NotebookLM status
];
```

## RunTimeline Component

```jsx
// Étapes visuelles d'un run pipeline
const PIPELINE_STEPS = [
  { id: 'calendar',    label: 'Trigger Calendar',    icon: Calendar },
  { id: 'research',    label: 'Gemini Deep Research', icon: Search },
  { id: 'editorial',   label: 'Claude Editorial',    icon: Pen },
  { id: 'wordpress',   label: 'WordPress Publish',   icon: Globe },
  { id: 'logbook',     label: 'Logbook Post',        icon: BookOpen },
  { id: 'sheets',      label: 'Sheets Dashboard',    icon: BarChart },
];
```

## Checklist Livraison
- [ ] Polling interval configurable (défaut 30s)
- [ ] Gestion erreur si `.dashboard_config.json` absent
- [ ] Mobile : sidebar collapse en bottom nav sur < 640px
- [ ] Dark mode natif (les tokens sont déjà dark-first)
- [ ] Export CSV depuis le tableau des runs
