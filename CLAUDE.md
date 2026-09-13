# val2026

Domänanalys av valmanifest med utforskningsverktyg och valkompass.

## pipeline-config

```yaml
project:
  name: val2026
  app_dir: app
  language: python
version:
  file: domains/taxonomi.yaml
  scheme: semver
  key: "version:"
branch:
  model: shared-main
  integration_branch: main
verify:
  commands:
    - "python3 domains/extrahera.py"
    - "python3 -m pytest tests/ -q"
  health: "curl -sf http://127.0.0.1:5001/ > /dev/null"
  process: "python3 app/app.py"
deploy:
  target: local
  note: >-
    Lokalt är produktion. Appen binder till 0.0.0.0:5001 för test på internt
    nät och skriver ut nätverksadressen vid start. Ingen autentisering -
    endast betrodda nät.
guardrails:
  - "Taggning är heuristisk. Varje vy som visar härledd data måste redovisa sin osäkerhet."
  - "Frånvaro av belägg får aldrig tolkas som motstånd. 'saknas' är ett eget tillstånd, aldrig 0."
  - "Matchningsprocent visas aldrig utan täckningssiffra."
  - "Originaltext och källhänvisning sparas på varje härledd enhet, alltid spårbart bakåt."
  - "Inga rekommendationer eller tolkande sammanfattningar av resultat."
  - "Config-over-hardcode: taxonomin styr domäner, inte kod."
commit:
  trailer: "Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

## Pipeline

CR:er författas av cr-intake, implementeras av cr-ship.
Status: Draft -> Proposed -> Planned -> Implemented -> Archived.
CR-katalog: `docs/change-requests/`.
