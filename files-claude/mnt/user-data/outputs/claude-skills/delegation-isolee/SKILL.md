---
name: delegation-isolee
description: Règles pour déléguer les tâches lourdes en contexte à des sous-agents économiques (Haiku). Invoke avec /delegation-isolee.
disable-model-invocation: true
---

# Isolation du Contexte par Sous-agents

## Principe Core
Les sous-agents fonctionnent dans une **fenêtre de contexte isolée** → le contexte principal reste propre.

## Tâches à déléguer OBLIGATOIREMENT à Haiku

| Tâche | Modèle | Output attendu |
|-------|--------|----------------|
| Analyse de logs longs | `haiku` | Ligne d'erreur + context (5 lignes) |
| Couverture de tests | `haiku` | % + liste des tests FAIL uniquement |
| Lecture de documentation volumineuse | `haiku` | Résumé < 200 mots |
| Scan de dépendances | `haiku` | Liste des conflits uniquement |
| Validation JSON/YAML | `haiku` | ✅ valide ou ❌ + ligne erreur |

## Configuration sous-agent

```python
# Template de délégation
subagent_config = {
    "model": "claude-haiku-4-5",
    "max_tokens": 500,  # Forcer la concision
    "system": "Tu es un agent de filtrage. Retourne UNIQUEMENT l'information essentielle demandée. Pas d'explication, pas de contexte superflu.",
    "task": "[TÂCHE SPÉCIFIQUE]"
}
```

## Règle de Retour
Le sous-agent retourne **uniquement** :
- ✅ La ligne exacte de l'erreur
- ✅ Un résumé concis (< 200 mots)
- ❌ Jamais le fichier complet
- ❌ Jamais d'explications non demandées

## Application GorgusWorld / BlueOceanLabs

### Batch API nocturne
→ Déléguer la validation des outputs batch à Haiku
→ Haiku filtre et retourne uniquement les erreurs de génération

### Pipeline MCP Canva
→ Déléguer la lecture des logs de transaction
→ Haiku retourne : `commit: ✅` ou `erreur: [message]`

### Google Sheets CMS (22 colonnes)
→ Déléguer la validation des 100 lignes
→ Haiku retourne : lignes manquantes + colonne concernée

### BlueOceanLabs FastAPI
→ Déléguer l'analyse des logs d'erreurs API
→ Haiku retourne : endpoint + status code + message

## Fresh Context Protocol
Si 2 tentatives de debug échouent → **nouveau chat Claude Code** + délégation à Haiku pour isoler l'erreur proprement.
