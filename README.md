# api_restatify-tensegrity-ai-hive

**Tensegrity AI Hive**: nimmt gefaltete Deltas und Strukturmeldungen an, webt sie vertrauensgewichtet zusammen,
unterteilt sie in Fachgebiets-Experten, prüft Kandidaten im Eval-Gate und verteilt signierte Releases. Der Hive
trainiert nicht auf Rohdaten.

## Rollen (per Konfiguration)

| Rolle | Einsatz |
|---|---|
| Root / Upstream | Internet-Hive |
| Klon | Organisation, Intranet (air-gapped), Land; prüft Upstream-Signaturen und signiert neu |

Kaskaden sind möglich. Intranet-Hives importieren per Datenträger; Export ist optional und schließt „Streng geheim“
immer aus.

## Geplante Module

Annahme und Stufenprüfung · Trust/Blacklist (T(a), f_betreiber) · Weben (FedAvg) · Slot-Registry · Unterteilen ·
Eval-Gate · Release (TUF) · Import/Export · Admin-API · GGUF-Export.

## Technik

Python, PyTorch, PEFT, TRL, PostgreSQL, MinIO/S3, gRPC. Betrieb mit Docker Compose (auch air-gapped mit GPU) oder Helm.

## Dokumentation

Siehe [docs_restatify-tensegrity-ai](https://github.com/carryman1979/docs_restatify-tensegrity-ai).

## Lizenz

Apache License 2.0 – siehe [LICENSE](LICENSE).
