# API Client Module

Framework-agnostische API-Abstraktion für das eRechnung Django Backend.

## Struktur

```
src/api/
├── client.js              # Axios-Client mit JWT-Interceptors
└── services/              # Service-Layer (Business-Logik)
    ├── authService.js     # Authentifizierung
    ├── invoiceService.js  # Rechnungen
    ├── companyService.js  # Unternehmen (Aussteller)
    ├── customerService.js # Kunden (Empfänger)
    ├── productService.js  # Produkte/Dienstleistungen
    ├── attachmentService.js # Dateianhänge
    └── index.js           # Service-Exports
```

## Verwendung

### Import

```javascript
// Single Service
import { invoiceService } from '@/api/services/invoiceService'

// Alle Services
import { authService, invoiceService } from '@/api/services'
```

### Beispiel: Login

```javascript
import { authService } from '@/api/services'

try {
  const { access, refresh, user } = await authService.login('username', 'password')
  console.log('Logged in:', user)
} catch (error) {
  console.error('Login failed:', error)
}
```

### Beispiel: Rechnungen laden

```javascript
import { invoiceService } from '@/api/services'

// Alle Rechnungen
const data = await invoiceService.getAll()

// Mit Filtern
const filtered = await invoiceService.getAll({
  page: 1,
  page_size: 20,
  status: 'PAID',
  search: 'Kunde XY'
})

// Einzelne Rechnung
const invoice = await invoiceService.getById(42)
```

### Beispiel: PDF/XML Download

```javascript
import { invoiceService } from '@/api/services'

// PDF herunterladen
const pdfBlob = await invoiceService.downloadPDF(42)

// Hybrid-PDF (mit eingebettetem XML)
const hybridBlob = await invoiceService.downloadHybridPDF(42)
```

## Authentifizierung

Der API-Client verwaltet JWT-Tokens automatisch:

1. **Request-Interceptor**: Fügt `Authorization: Bearer <token>` zu jedem Request hinzu
2. **Response-Interceptor**: Bei 401 Fehler → Token-Refresh oder Logout

## Error Handling

```javascript
import { invoiceService } from '@/api/services'
import { getErrorMessage } from '@/utils/errorHandling'

try {
  const invoice = await invoiceService.getById(42)
} catch (error) {
  const message = getErrorMessage(error)
  console.error(message)
}
```

## Framework-Agnostisch

Der Service-Layer ist unabhängig von Vue.js und kann für React/Angular/etc. wiederverwendet werden.
