# CLAUDE.md – api_restatify-tensegrity-ai-hive

Python-Hive. Fachliche Referenz: Docs-Repo (Whitepaper V1.0.26 Abschnitt 4, ADR-0006/7/10).

## Regeln
- Keine Rohdaten annehmen; Einreichungen mit Stufe Streng geheim + Gewichten verwerfen und protokollieren.
- Weben nur über Offen/Vertraulich mit T(a) > 0; jedes Kandidaten-Release durch das Eval-Gate.
- Rolle, Vertrauensanker und Endpunkte ausschließlich aus Konfiguration – nichts fest verdrahten.
- Betreiber-Eingriffe (f_betreiber, Blacklist, Richtlinien) ins Audit-Log.
- Tests: `pytest` (Unit/Komponente), Testcontainers für Postgres/MinIO (Integration), `hypothesis` für Aggregation.
- Lizenzen mit `pip-licenses` prüfen.
- Kein `git push` ohne Freigabe.
