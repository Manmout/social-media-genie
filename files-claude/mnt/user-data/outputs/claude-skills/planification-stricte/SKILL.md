---
name: planification-stricte
description: Protocole obligatoire avant toute modification de code. Évite les impasses coûteuses et la sur-ingénierie. Invoke avec /planification-stricte.
disable-model-invocation: true
---

# Protocole de Planification (Plan Mode)

## Les 4 Lois Immuables

### Loi 1 — Explorer avant de toucher
N'apporte **aucune modification** sans avoir une confiance à **95%** sur la marche à suivre.
- Pose des questions ciblées si nécessaire
- Un doute = une question, pas une tentative

### Loi 2 — Plan avant le code
Présente toujours un **plan d'implémentation** structuré avant de coder :
```
📋 Plan proposé :
1. [Étape 1 — fichier(s) concerné(s)]
2. [Étape 2 — changement précis]
3. [Impact estimé — tokens / complexité]
→ Validation requise avant exécution
```

### Loi 3 — Périmètre strict (No Scope Creep)
Fait **uniquement** les modifications demandées :
- ❌ Refactorisation du code adjacent non demandée
- ❌ Fonctionnalités non sollicitées
- ❌ "Améliorations" spontanées
- ✅ Exactement ce qui est demandé, rien de plus

### Loi 4 — Nettoyage post-tâche
Une fois la tâche accomplie, rappeler systématiquement :
> ✅ Tâche terminée. Lance `/clear` avant la prochaine tâche non liée pour vider le contexte.

## Application GorgusWorld

| Tâche | Action requise |
|-------|---------------|
| Nouveau livre (scène) | Plan des 14 scènes + validation |
| Pipeline MCP (Canva/Brevo) | Sequence start→perform→commit à valider |
| Batch API nocturne | Estimer coût avant lancement |
| Nouveau slash command | Décrire comportement attendu avant code |
| BlueOceanLabs endpoint | Spécifier input/output avant FastAPI |

## Ultrathink Check
Avant chaque modification :
- [ ] Architecture claire en tête ?
- [ ] Solution élégante et réutilisable ?
- [ ] Moins de 3 fichiers modifiés ?
- [ ] Périmètre validé avec Manmout ?
