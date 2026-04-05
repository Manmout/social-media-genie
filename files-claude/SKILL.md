---
name: recherche-econome
description: Méthodes strictes pour chercher et naviguer dans le code sans gaspiller de jetons. Invoke avec /recherche-econome.
disable-model-invocation: true
---

# Navigation et Extraction Optimisées

## Règle d'Or
**Ne lis JAMAIS un fichier entier pour comprendre sa structure.**

## Stratégies par ordre de priorité

### 1. Signatures uniquement (AST)
Utilise `universal-ctags` ou `tree-sitter` pour extraire :
- Signatures de fonctions
- Définitions de classes
- Dépendances et imports
→ Jamais l'implémentation complète

```bash
# Extraire toutes les fonctions d'un fichier
ctags -x --fields=+n file.js | grep function

# Vue arborescence projet (2 niveaux max)
find . -maxdepth 2 -type f -name "*.js" | head -30
```

### 2. Recherche ciblée (Grep/Semgrep)
Pour localiser du code précis :
```bash
# Chercher une fonction spécifique
grep -n "nomDeFonction" --include="*.js" -r src/

# Pattern structurel (semgrep)
semgrep --pattern "async function $FUNC(...) { ... }" src/
```

### 3. Plans de repo (si disponibles)
Privilégier les plans pré-générés :
- `repomix` (XML structuré)
- `gptrepo`
- `tree` (2 niveaux max)

→ Ne jamais scanner récursivement sans filtre

## Interdit
- ❌ `cat fichier_long.js` pour "comprendre"
- ❌ Lecture de `node_modules/`, `dist/`, `build/`
- ❌ Scan récursif sans filtre de profondeur

## Contexte GorgusWorld / BlueOceanLabs
- Entrée principale : `CLAUDE.md` → puis skills spécifiques uniquement
- MCP Stack : accès via commandes, pas lecture directe des configs
- CMS Google Sheets : lire via MCP, jamais les fichiers CSV bruts
