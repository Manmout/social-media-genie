# 🚀 Déploiement — Skills Token-Efficiency
# Artclic Studios / GorgusWorld / BlueOceanLabs

## Structure à créer

```
C:\Users\njeng\
├── .claudeignore                          ← à la racine de chaque projet
├── .claude/
│   ├── settings.json
│   └── skills/
│       ├── recherche-econome/
│       │   └── SKILL.md
│       ├── planification-stricte/
│       │   └── SKILL.md
│       ├── delegation-isolee/
│       │   └── SKILL.md
│       └── execution-propre/
│           └── SKILL.md
```

## Commandes PowerShell de déploiement

```powershell
# Depuis la racine de ton projet principal (ex: gorgusworld-mcp)
cd C:\Users\njeng\gorgusworld-mcp

# Créer la structure
New-Item -ItemType Directory -Force -Path ".claude\skills\recherche-econome"
New-Item -ItemType Directory -Force -Path ".claude\skills\planification-stricte"
New-Item -ItemType Directory -Force -Path ".claude\skills\delegation-isolee"
New-Item -ItemType Directory -Force -Path ".claude\skills\execution-propre"

# Copier les fichiers depuis les outputs Claude
# (après téléchargement depuis Claude.ai)
Copy-Item "recherche-econome\SKILL.md" ".claude\skills\recherche-econome\SKILL.md"
Copy-Item "planification-stricte\SKILL.md" ".claude\skills\planification-stricte\SKILL.md"
Copy-Item "delegation-isolee\SKILL.md" ".claude\skills\delegation-isolee\SKILL.md"
Copy-Item "execution-propre\SKILL.md" ".claude\skills\execution-propre\SKILL.md"
Copy-Item ".claudeignore" ".claudeignore"
Copy-Item ".claude\settings.json" ".claude\settings.json"
```

## Usage dans Claude Code

| Commande | Quand l'utiliser |
|----------|-----------------|
| `/recherche-econome` | Avant d'explorer une codebase inconnue |
| `/planification-stricte` | Avant TOUTE modification de code |
| `/delegation-isolee` | Face à des logs/docs volumineux |
| `/execution-propre` | Avant de lancer des tests ou installs |

## Projets concernés

Déployer dans CHACUN de ces répertoires :
- `C:\Users\njeng\gorgusworld-mcp\` (pipeline principal)
- `C:\Users\njeng\blueocean-labs\` (micro-SaaS)
- `C:\Users\njeng\hemle\` (site transmedia)
- `C:\Users\njeng\artclic-indie-maker\` (CLAUDE-INDIE-MAKER)

## Économies estimées

| Optimisation | Économie tokens |
|-------------|-----------------|
| `.claudeignore` agressif | ~60-80% des lectures |
| Skills non chargés au démarrage | ~2000-5000 tokens/session |
| Filtrage sorties terminal | ~1000-3000 tokens/tâche |
| Sous-agents Haiku pour logs | ~80% coût vs Sonnet |

## 🎯 ROI mensuel estimé (100 livres/an)

- Avant : ~X tokens/pipeline
- Après : ~30-40% moins
→ Budget Batch API nocturne optimisé
