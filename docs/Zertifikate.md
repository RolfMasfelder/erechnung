# Digitale Signaturen für ausgehende Rechnungen

> Erstellt: 09.03.2026
> Kontext: TODO 3.5 — Integration Features → Digitale Signaturen

---

## Ziel

Ausgehende PDF/A-3-Rechnungen digital signieren, damit der Empfänger:
1. **Integrität** prüfen kann (Rechnung wurde nicht verändert)
2. **Absender-Authentizität** verifizieren kann (Rechnung stammt von uns)
3. **Zeitpunkt** der Signatur belegt ist (vertrauenswürdiger Zeitstempel)

---

## Signatur-Verfahren: PAdES (PDF Advanced Electronic Signatures)

PAdES ist der Standard für digitale Signaturen in PDF-Dokumenten und passt zur bestehenden PDF/A-3-Pipeline (pikepdf).

### Signatur-Stufen

| Stufe | Inhalt | GoBD/Archiv | Empfehlung |
|-------|--------|-------------|------------|
| PAdES-B-B | Basis-Signatur mit Zertifikat | Grundschutz | Nur für PoC |
| PAdES-B-T | + Vertrauenswürdiger Zeitstempel | Gut | **Minimum für Produktion** |
| PAdES-B-LT | + Validierungsdaten eingebettet (CRL/OCSP) | Empfohlen | **Gut für GoBD** |
| PAdES-B-LTA | + Archiv-Zeitstempel | Ideal für 10-Jahres-GoBD | Maximale Rechtssicherheit |

---

## Signatur-Ablauf (lokal, kein Datenabfluss)

```
PDF/A-3 Rechnung
       │
       ▼
  SHA-256 Hash berechnen           ← lokal (32 Bytes)
       │
       ▼
  Hash mit privatem Schlüssel      ← lokal (kryptographisch)
  signieren
       │
       ▼
  Signatur + Zertifikat            ← lokal (pyhanko)
  in PDF einbetten
       │
       ▼
  Hash an Zeitstempel-Server       ← nur der Hash (32 Bytes)!
  (TSA) senden
       │
       ▼
  Zeitstempel-Token in PDF         ← lokal
  einbetten
```

**Rechnungsdaten (Beträge, Kunden, Positionen) verlassen zu keinem Zeitpunkt den Server.** Der Zeitstempel-Server sieht nur einen kryptographischen Hash — daraus lässt sich der Inhalt nicht rekonstruieren.

---

## Zertifikat-Erstellung (einmalig)

1. **Lokal** ein Schlüsselpaar erzeugen (privater + öffentlicher Schlüssel)
2. **CSR** (Certificate Signing Request) an CA senden — enthält nur: Firmenname, Adresse, E-Mail. Keine Rechnungsdaten.
3. CA prüft Identität (Handelsregister, Personalausweis etc.)
4. Man erhält ein **Zertifikat** (`.p12`/`.pfx`-Datei) — gültig 1–3 Jahre

Der **private Schlüssel verlässt nie den Server.**

### Veröffentlichung des öffentlichen Schlüssels

Der öffentliche Schlüssel wird **nicht separat veröffentlicht** — er ist im Zertifikat eingebettet, und das Zertifikat wird in die signierte PDF eingebettet. Der Empfänger erhält also alles Nötige mit der Rechnung:

```
┌─────────────────────────────────────────┐
│  Signierte PDF/A-3 Rechnung             │
│  ├── factur-x.xml                       │
│  ├── Signatur (erstellt mit priv. Key)  │
│  └── Zertifikat (enthält öff. Key       │
│       + Firmendaten + CA-Bestätigung)   │
└─────────────────────────────────────────┘
```

### Prüfung durch den Empfänger

1. Zertifikat aus PDF lesen → enthält den öffentlichen Schlüssel
2. Signatur mit öffentlichem Schlüssel mathematisch prüfen
3. Trust Chain prüfen: Wurde dieses Zertifikat von einer vertrauenswürdigen CA signiert?
4. Zeitstempel prüfen

Schritt 3 funktioniert, weil Adobe Reader, Windows und macOS **Root-Zertifikate** der großen CAs vorinstalliert haben. Kein manueller Import nötig.

---

## Zertifikat-Anbieter (Auswahl)

### Fortgeschrittene Zertifikate (AdES)

| Anbieter | Preis/Jahr (ca.) | Besonderheit |
|----------|-------------------|-------------|
| **Sectigo** (ehem. Comodo) | 30–80€ | Günstig, international anerkannt |
| **SSL.com** | 60–120€ | PKCS#12 direkt downloadbar |
| **GlobalSign** | 100–250€ | Document Signing Certificates |
| **DigiCert** | 100–200€ | Breite PDF-Reader-Unterstützung |

### Qualifizierte Zertifikate (QES, eIDAS)

| Anbieter | Preis/Jahr (ca.) | Besonderheit |
|----------|-------------------|-------------|
| **D-Trust** (Bundesdruckerei) | 150–300€ | Deutsche Vertrauensstelle, eIDAS-konform |
| **SwissSign** | 200–400€ | CH/EU anerkannt |

---

## D-Trust vs. DigiCert — Vergleich

| Kriterium | D-Trust | DigiCert |
|-----------|---------|----------|
| **Sitz** | Berlin (Bundesdruckerei) | USA (Lehi, Utah) |
| **Zertifikats-Typ** | Qualifiziert (QES) + Fortgeschritten | Fortgeschritten |
| **eIDAS-Konformität** | Ja, qualifizierter TSP | Nein (nicht qualifiziert i.S.v. eIDAS) |
| **Rechtliche Wirkung** | Handschrift-Äquivalent (eIDAS Art. 25.2) | Integritätsnachweis, keine Handschrift-Gleichstellung |
| **Adobe Trust List (AATL)** | Ja | Ja |
| **Preis** | 150–300€/Jahr | 100–200€/Jahr |
| **Identitätsprüfung** | Streng (Personalausweis, ggf. vor Ort) | Firmenprüfung (Handelsregister, Telefon) |
| **Zeitstempel-Server** | Qualifizierter TSA (kostenpflichtig) | Kostenloser TSA inkludiert |
| **Lieferform** | Signaturkarte oder Soft-Zertifikat (.p12) | Soft-Zertifikat (.p12) |
| **Sprache/Support** | Deutsch | Englisch |
| **Ideal für** | Maximale Rechtssicherheit in DE/EU | Pragmatische Lösung, international |

### Empfehlung

- **D-Trust** wählen, wenn: Qualifizierte Signatur (QES) gewünscht ist, z.B. weil Empfänger das fordern oder die Signatur eine handschriftliche Freigabe ersetzen soll. Maximale Rechtssicherheit im deutschen/EU-Rechtsraum.

- **DigiCert** wählen, wenn: Fortgeschrittene Signatur ausreicht (Integritäts- und Absendernachweis). Pragmatisch, günstiger, unkomplizierter Bezug als `.p12`-Datei.

**Hinweis:** E-Rechnungen nach EN16931 erfordern *keine* qualifizierte Signatur. Die Signatur dient primär dem Integritätsnachweis. Ein fortgeschrittenes Zertifikat + vertrauenswürdiger Zeitstempel ist dafür ausreichend.

---

## Zeitstempel-Server (RFC 3161 TSA)

| Dienst | Preis | URL |
|--------|-------|-----|
| **FreeTSA** | Kostenlos | `https://freetsa.org/tsr` |
| **Sectigo** | Kostenlos | `http://timestamp.sectigo.com` |
| **DigiCert** | Im Zertifikat inkl. | `http://timestamp.digicert.com` |
| **GlobalSign** | Im Zertifikat inkl. | `http://timestamp.globalsign.com` |
| **D-Trust** | Qualifiziert, kostenpflichtig | Vertragsabhängig |

---

## Technische Umsetzung

### Library: `pyhanko`

- Reines Python, aktiv gepflegt
- PDF/A-3-kompatibel
- Unterstützt alle PAdES-Stufen (B-B bis B-LTA)
- PKCS#12-Zertifikate (.p12/.pfx)
- Sichtbare Signaturfelder optional
- RFC 3161 Zeitstempel-Client integriert

### Konfiguration (geplant)

Umgebungsvariablen:
- `PDF_SIGNING_CERT_PATH` — Pfad zur .p12-Datei
- `PDF_SIGNING_CERT_PASSWORD` — Passwort für die .p12-Datei
- `PDF_SIGNING_TSA_URL` — Zeitstempel-Server URL
- `PDF_SIGNING_ENABLED` — Signierung aktivieren (true/false)

### Integration in bestehende Pipeline

Signierung erfolgt als letzter Schritt nach der PDF/A-3-Generierung (pikepdf):

```
XML generieren → PDF rendern → PDF/A-3 konvertieren → Attachments einbetten → PAdES signieren
```

### Aufwand-Abschätzung

| Variante | Aufwand |
|----------|---------|
| Selbstsigniert (PoC, nur für Tests) | ~4h |
| Fortgeschrittenes Zertifikat + TSA (Sectigo/DigiCert) | ~8h |
| Qualifiziertes Zertifikat + QES (D-Trust) | ~12–16h |

---

## Was wird wohin übermittelt? (Datenschutz-Zusammenfassung)

| Schritt | Daten | Empfänger | Häufigkeit |
|---------|-------|-----------|------------|
| Zertifikat kaufen | Firmenname, Adresse, CSR | Zertifikatsstelle | Einmalig (alle 1–3 Jahre) |
| Rechnung signieren | **Nichts** (lokal) | — | Pro Rechnung |
| Zeitstempel holen | **Nur SHA-256 Hash** (32 Bytes) | TSA-Server | Pro Rechnung |
| Rechnung versenden | Signierte PDF (inkl. Zertifikat) | Rechnungsempfänger | Pro Rechnung |
