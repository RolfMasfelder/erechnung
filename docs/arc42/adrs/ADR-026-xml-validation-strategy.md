# ADR 026: XML Validation Strategy (XSD + Schematron via Saxon-HE)

## Status

**Accepted** — 2026-04-30 (retrospective documentation of the implementation merged 2026-03-05, see TODO §2.5).

## Date

2026-04-30 (implementation merged 2026-03-05, see TODO §2.5)

## Context

EN 16931-konforme Eingangs- und Ausgangsrechnungen müssen sowohl strukturell (XSD) als auch
geschäftsregel-basiert (Schematron) validiert werden. Strukturelle XSD-Prüfung allein reicht nicht:
EN 16931 definiert tausende Business Rules, die nur per Schematron ausdrückbar sind
(z. B. „BT-10 Pflicht bei XRechnung-Profil", VAT-Konsistenz, Summenprüfungen).

Anforderungen:

- Vollständige Abdeckung der **CEN/TC 434 EN 16931-1** Schematron-Regeln (ConnectingEurope-XSLT).
- Erweiterbarkeit für strengere Profile (XRechnung KoSIT 3.0 — siehe ADR-027).
- Lauffähig in derselben Python-Codebase wie der Rest der Invoice-Pipeline (kein separater Java-Service).
- Performant genug für interaktive Validierung im Web-Backend.

## Decision

**XSD-Validierung mit `lxml`** (FacturX-/CII-Schema) + **Schematron-Validierung mit `saxonche`**
(Saxon-HE 12, Python-Bindings). Beide Backends werden über einen `CombinedBackend`
hintereinander ausgeführt; Fehler/Warnungen werden zu einem einheitlichen Validation-Result
zusammengeführt.

Die offizielle EN 16931 Schematron-Distribution ist als XSLT 2.0 vorkompiliert. Damit ist eine
**XSLT-2.0-fähige Engine zwingend** — das schließt `lxml` (nur XSLT 1.0) aus. Saxon-HE ist die
Referenz-Implementierung für XSLT 2.0/3.0 und steht über `saxonche` als Python-Wheel zur
Verfügung (kein separates JRE nötig).

### Implementierung

- `invoice_app/utils/xml/backends.py`:
  - `XsdOnlyBackend` — `lxml.etree.XMLSchema`
  - `SchematronSaxonBackend` — Saxon-CE (`saxonche`) lädt vorgefertigtes Schematron-XSLT
  - `CombinedBackend` — Sequence: XSD zuerst (Strukturfehler abbrechen), dann Schematron
- `invoice_app/utils/xml/validator.py` wählt den Backend-Mix abhängig von verfügbaren Schemata.
- XSLT-Dateien liegen versioniert im Repo (kein Download zur Laufzeit).

## Considered Alternatives

| Alternative | Verworfen weil |
|---|---|
| **Pure-Python ISO-Schematron (z. B. `pyschematron`)** | Unterstützt nur eingeschränkt XSLT 2.0; aktuelle EN 16931 Distribution nicht direkt nutzbar; Performance-Einbußen. |
| **Java-basierter Validator als Sidecar (z. B. KoSIT Validator JAR)** | Zusätzliche Runtime-Abhängigkeit (JRE), separater Prozess, IPC-Overhead, Container-Image deutlich größer. |
| **Online-Validator (z. B. ConnectingEurope Web-Service)** | Externe Abhängigkeit, DSGVO-/GoBD-relevant (Daten verlassen Haus), nicht offline-fähig. |
| **lxml-only (XSD)** | Schematron-Regeln nicht ausführbar — fundamentale Lücke gegenüber EN 16931. |

## Consequences

**Positive:**

- Vollständige EN 16931-Konformitätsprüfung in-process.
- Saxon-HE deckt XSLT 2.0/3.0 ab — auch zukünftige Schematron-Versionen lauffähig ohne Architekturänderung.
- `CombinedBackend`-Pattern erlaubt späteres Anhängen weiterer Validatoren (XRechnung KoSIT, Peppol BIS) ohne Eingriff in Aufrufer.
- Reine Python-Codebase (`saxonche` ist Wheel mit nativem Code, kein JRE).

**Negative / Trade-offs:**

- `saxonche`-Wheel ist plattformspezifisch (manylinux/macos/windows) — Build-Pipeline muss das berücksichtigen.
- Saxon-HE ist MPL-2.0-lizenziert (kompatibel, aber zusätzliche Lizenz im SBOM).
- Schematron-Validierung ist messbar langsamer als XSD (~50-200 ms pro Rechnung typisch); bei Bulk-Validierung im Import ggf. parallelisieren.

## Related Decisions

- **ADR-006** ZUGFeRD Profile Selection — definiert *welche* Profile validiert werden.
- **ADR-027** XRechnung 3.0 / KoSIT-Konformität — baut auf `CombinedBackend` auf.
- **ADR-008** Error Handling & Validation Strategy — konsumiert die `ValidationResult`-Struktur.

## References

- EN 16931-1 — Electronic invoicing; semantic data model
- ConnectingEurope EN16931 Schematron: https://github.com/ConnectingEurope/eInvoicing-EN16931
- Saxon-HE / saxonche: https://www.saxonica.com/saxon-c/index.xml
- TODO 2026 §2.5 (Implementierungs-Erledigt-Vermerk 05.03.2026)
