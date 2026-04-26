# Anti-Corruption Layer: UI ↔ API Field Mapping

## Pattern

Die Kommunikation zwischen Vue.js-Frontend und Django REST API erfolgt über eine
**Anti-Corruption Layer (ACL)** — eine explizite Übersetzungsschicht, die in
`frontend/src/api/fieldMappings.js` zentral definiert ist.

**Kernprinzip:** Jedes Feld, das die Grenze UI ↔ API überquert, **muss** in der
Mapping-Deklaration aufgeführt sein — auch wenn UI- und API-Name identisch sind.
Zufällig passende Feldnamen sind nicht akzeptabel.

## Warum?

Ohne explizites Mapping entstehen drei inkonsistente Fälle:

1. **Zufällig gleiche Namen** werden stillschweigend durchgereicht — bricht bei Rename auf einer Seite
2. **Unterschiedliche Namen** werden inline in Komponenten umbenannt — verstreute Logik, schwer zu finden
3. **Felder die nur auf einer Seite existieren** werden stillschweigend geschluckt — schwer zu debuggen

Die ACL eliminiert alle drei Fälle durch eine **Whitelist-Semantik**: Nur deklarierte
Felder passieren die Grenze, alles andere wird verworfen.

## Aufbau

### Mapping-Deklaration (pro Entity)

```javascript
export const invoiceFields = createFieldMapper({
  UI_TO_API: {
    // UI-Feldname        → API-Feldname
    invoice_number:        'invoice_number',        // 1:1
    business_partner:      'business_partner',      // 1:1
    // ... alle Felder explizit gelistet
  },
  UI_ONLY: new Set([
    // Felder die nur im UI existieren (z.B. für Validierung)
  ]),
})
```

### Verwendung in Services

```javascript
import { invoiceFields } from '../fieldMappings'

async function create(data) {
  const response = await api.post('/invoices/', invoiceFields.toApi(data))
  return invoiceFields.fromApi(response.data)
}
```

### Richtungen

| Funktion   | Richtung    | Verhalten |
|------------|-------------|-----------|
| `toApi()`  | UI → API    | Benennt Felder um, entfernt `UI_ONLY`-Felder, verwirft unbekannte Felder |
| `fromApi()` | API → UI   | Benennt zurück, reicht Read-Only-Felder (id, created_at, …) durch |

## Regeln für Entwickler

1. **Neue Felder** → Zuerst in `docs/openapi.json` deklarieren, dann in `fieldMappings.js` aufnehmen
2. **Feld umbenennen** → Nur an einer Stelle in `fieldMappings.js` ändern, UI- und API-Code bleiben stabil
3. **Kein direkter Zugriff auf API-Feldnamen** in Vue-Komponenten oder Stores — immer über den Service, der das Mapping nutzt
4. **Neue Entity** → Neues Mapping in `fieldMappings.js` anlegen, Factory `createFieldMapper()` verwenden
5. **Tests** → `frontend/src/api/__tests__/fieldMappings.test.js` erweitern

## Betroffene Entities

| Entity           | Besonderheiten |
|------------------|----------------|
| Invoice          | Nested Lines + AllowanceCharges mit eigenen Mappings |
| InvoiceLine      | `unit_price_net` (UI) → `unit_price` (API), `vat_rate` → `tax_rate` |
| AllowanceCharge  | 1:1 Mapping |
| BusinessPartner  | `name` → `company_name`, `street` → `address_line1`, `tax_number` → `tax_id` |
| Company          | 1:1 Mapping |
| Product          | `base_price` → `unit_price`, `default_tax_rate` → `tax_rate` |
| Attachment       | 1:1 Mapping |

## Verwandte Dateien

- `frontend/src/api/fieldMappings.js` — Zentrale Mapping-Definitionen
- `frontend/src/api/__tests__/fieldMappings.test.js` — Tests (18 Tests)
- `frontend/src/api/services/*.js` — Services die `toApi()`/`fromApi()` nutzen
- `docs/openapi.json` — Single Source of Truth für API-Feldnamen
