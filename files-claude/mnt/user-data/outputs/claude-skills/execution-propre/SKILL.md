---
name: execution-propre
description: Bonnes pratiques pour l'exécution d'outils et le filtrage des sorties terminal. Minimise les tokens de sortie. Invoke avec /execution-propre.
disable-model-invocation: true
---

# Optimisation des Outils et du Terminal

## Règle Fondamentale
**Les sorties terminal non filtrées sont la source #1 de gaspillage de tokens.**

## CLI Natifs > Serveurs MCP

Toujours préférer les CLI natifs pour les interactions ponctuelles :

| Service | Préférer | Éviter |
|---------|---------|--------|
| GitHub | `gh` CLI | MCP GitHub complet |
| AWS | `aws` CLI | MCP AWS |
| Google Cloud | `gcloud` CLI | MCP GCloud |
| Brevo | API REST direct | MCP si non nécessaire |

→ Les CLI n'ajoutent **pas** de définitions d'outils persistantes dans le contexte.

## Filtrage Obligatoire des Sorties

### Tests
```powershell
# PowerShell (environnement Manmout - Windows)
npm test | Select-String "FAIL|ERROR|✗" | Select-Object -First 20

# Node / Jest
npx jest --verbose 2>&1 | Select-String "FAIL|PASS|Error" | Select-Object -Last 30

# Python pytest
python -m pytest 2>&1 | Select-String "FAILED|ERROR|passed|failed" | Select-Object -Last 10
```

### Installations
```powershell
# npm install - n'afficher que les erreurs
npm install 2>&1 | Select-String "ERR|warn|error" 

# pip install
pip install -r requirements.txt 2>&1 | Select-String "ERROR|error|Successfully"
```

### Logs serveur
```powershell
# Ne lire que les 20 dernières lignes
Get-Content server.log -Tail 20

# Filtrer erreurs uniquement
Get-Content server.log | Select-String "ERROR|WARN|Exception"
```

## Désactivation des MCP Inutiles

Avant chaque session, identifier les MCP actifs :
- GorgusWorld : Canva + Sheets + Brevo + Lulu + Telegram
- BlueOceanLabs : FastAPI local uniquement
- Hemle : Netlify CLI + Notion MCP

→ Désactiver les MCP non nécessaires pour la tâche en cours.

## Hooks PreToolUse (settings.json)

Configurés pour intercepter automatiquement :
- Sorties `npm test` → tronquer à 20 lignes d'erreurs
- Sorties `pytest` → filtrer PASSED
- Sorties `git log` → limiter à 10 commits

Voir `.claude/settings.json` → section `hooks`.

## Spécificités PowerShell (Windows - C:\Users\njeng)

⚠️ Rappels critiques :
- Continuation de ligne : backtick `` ` `` (pas `\`)
- Séparateur de chemin : `\\` ou `/` (tester les deux si erreur)
- Pipe : `|` fonctionne normalement
- Variables : `$env:VAR_NAME` pour les variables d'environnement
