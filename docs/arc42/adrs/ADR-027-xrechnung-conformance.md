# ADR 027: XRechnung 3.0 (KoSIT) Conformance & Leitweg-ID Handling

## Status

**Accepted** — 2026-04-30 (retrospective documentation; implementation see TODO §3.10).

## Date

2026-04-30 (implementation see TODO §3.10)

## Context

Ab dem 27.11.2020 sind öffentliche Auftraggeber des Bundes verpflichtet, elektronische Rechnungen
nach **XRechnung** anzunehmen (E-Rech-VO/ERechV §4). Die Bundesländer haben das in eigenen
Landesgesetzen nachgezogen. XRechnung ist eine **CIUS** (Core Invoice Usage Specification) auf Basis
EN 16931 mit zusätzlichen, strengeren Schematron-Regeln, die von der **KoSIT** (Koordinierungsstelle
für IT-Standards, Bremen) gepflegt werden.

Die Lösung muss B2B (ZUGFeRD/Factur-X, PDF/A-3 mit eingebetteter XML) **und** B2G (XRechnung als
reines XML oder Hybrid) abdecken — bei minimaler Code-Duplizierung, da der EN-16931-Kern identisch ist.

Spezifisch für XRechnung:

- Pflichtfeld **BT-10 Buyer Reference** (in Deutschland: **Leitweg-ID** des Empfängers).
- Leitweg-ID-Format: `\d{2,12}-[A-Za-z0-9]{1,30}-\d{2}` mit **Modulo-97-Prüfziffer nach ISO 7064** (Mod 97-10).
- XRechnung-spezifische Profil-URI als `BT-24 Specification identifier`.
- Strengere Schematron-Regeln gegenüber EN 16931 Core (KoSIT-Distribution).

## Decision

**Volle XRechnung-3.0-Konformität als zusätzliches Profil neben ZUGFeRD/Factur-X**, mit
folgenden Eckpunkten:

1. **Profil-Auswahl**:
   - `BusinessPartner.partner_type == GOVERNMENT` ⇒ XRechnung-Profil automatisch
     (`urn:cen.eu:en16931:2017#compliant#urn:xeinkauf.de:kosit:xrechnung_3.0`).
   - Alle anderen Empfänger nutzen das per Konfiguration gewählte ZUGFeRD-Profil.
   - Profil-URIs zentral in `PROFILE_MAP`.

2. **Leitweg-ID am `BusinessPartner`**:
   - Eigenes Feld `leitweg_id` (CharField max 46 Zeichen).
   - Validierung: Regex **plus** Modulo-97-Prüfziffer (ISO 7064 Mod 97-10).
   - Pflicht-Validierung wenn `partner_type == GOVERNMENT`.
   - Bei Rechnungserstellung an GOVERNMENT-Empfänger: `Invoice.buyer_reference` (BT-10) wird
     automatisch aus `leitweg_id` befüllt.

3. **Validierung über `CombinedBackend` (siehe ADR-026)**:
   - XSD weiterhin EN 16931 / CII.
   - Schematron: KoSIT-XRechnung-XSLT (strengere Regeln) **statt** des EN-16931-Core-Schematron,
     wenn das XRechnung-Profil aktiv ist.
   - BT-10-Pflichtigkeit wird durch das KoSIT-Schematron garantiert; doppelt geprüft im
     Service-Layer für frühe, sprechende Fehlermeldungen.

4. **Output-Varianten**:
   - **XML-only** für reine XRechnung-Workflows: separater Endpoint
     `POST /api/invoices/{id}/generate_xml/`, kein PDF/A-3-Wrapping.
   - **Hybrid (PDF/A-3 mit eingebetteter XRechnung-XML)** weiterhin möglich, aber für B2G nicht erforderlich.

5. **Scope-Abgrenzung — explizit *nicht* Teil dieses ADR**:
   - **Zustellung** der XRechnung (ZRE/OZG-RE/Peppol/E-Mail) — separat in TODO §3.11 erfasst.
   - Empfang eingehender XRechnungen — bereits durch die generelle Eingangs-Pipeline abgedeckt
     (Profil wird beim Import erkannt).

## Considered Alternatives

| Alternative | Verworfen weil |
|---|---|
| **Externes Service-Modul (separates Django-App-Modul)** | Künstliche Trennung — der XML-Kern ist zu 95 % identisch mit ZUGFeRD; Code-Duplizierung statt Code-Reuse. |
| **Hardcoded XRechnung-Profil als Default für alle** | ZUGFeRD ist im B2B-Geschäft Standard und wird in Deutschland breiter unterstützt; XRechnung als Default würde private Empfänger zu unrecht zwingen. |
| **Leitweg-ID nur als generisches Textfeld ohne Prüfziffer-Validierung** | Bundes-/Landesportale weisen invalide Leitweg-IDs ab — frühe Validierung im System verhindert spätere Zustell-Fehlschläge. |
| **EN-16931-Core-Schematron statt KoSIT-Schematron für XRechnung** | KoSIT ist strenger; ein im Core-Schematron passierter Datensatz kann am ZRE-Portal abgelehnt werden. Pflicht zum strengsten anwendbaren Profil. |

## Consequences

**Positive:**

- Vollwertige B2G-Fähigkeit ohne separaten Code-Pfad.
- Frühe Validierung der Leitweg-ID (Format + Prüfziffer) verhindert teure Spätfehler.
- KoSIT-Schematron deckt zusätzlich XRechnung-spezifische Business Rules ab, die EN-16931-Core nicht prüft.
- Architektur erweiterbar für weitere CIUS (z. B. Peppol BIS Billing 3.0 — siehe TODO §3.11 Stufe 4).

**Negative / Trade-offs:**

- Zwei Schematron-XSLT-Distributionen im Repo (EN 16931 + KoSIT); beide müssen bei Updates nachgezogen werden.
- KoSIT veröffentlicht regelmäßig Major-Updates (zuletzt 3.0.x) — Update-Prozess muss dokumentiert werden.
- `partner_type == GOVERNMENT` ist ein einfacher Boolean-Switch; Mischfälle (z. B. öffentliche
  Stiftung mit B2B-Charakter) müssen manuell entschieden werden.

## Related Decisions

- **ADR-006** ZUGFeRD Profile Selection.
- **ADR-026** XML Validation Strategy (XSD + Schematron via Saxon).
- **ADR-008** Error Handling & Validation Strategy.
- TODO §3.11 — XRechnung-Zustellung (Folge-ADR bei Implementierung).

## References

- EN 16931-1 — Electronic invoicing; semantic data model.
- KoSIT XRechnung 3.0: https://xeinkauf.de/xrechnung/
- Leitweg-ID Formatspezifikation (Bund + Länder).
- ISO 7064 — Mod 97-10 Prüfzifferverfahren.
- ERechV (E-Rech-VO) §4.
- TODO 2026 §3.10 (Implementierungsstand) und §3.11 (Zustellung).
