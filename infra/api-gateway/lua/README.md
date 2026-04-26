# Lua Scripts for API Gateway (Defense-in-Depth)

## jwt_validator.lua

Validates JWT tokens at the nginx perimeter **before** requests reach Django.

### Security Benefits

1. **DDoS-Schutz**: Ungültige Tokens werden in <1ms abgewiesen, ohne Django zu belasten
2. **Defense-in-Depth**: Unabhängige zweite Validierungsschicht neben Django SimpleJWT
3. **Perimeter-Sicherheit**: Nur authentifizierte Requests passieren den Gateway

### Funktionsweise

- Liest `JWT_SIGNING_KEY` aus Umgebungsvariable (identisch mit `DJANGO_SECRET_KEY`)
- Validiert HS256-Signatur und Token-Ablauf
- Auth-Endpoints (`/api/auth/`, `/api/token/`) sind ausgenommen
- Ohne `JWT_SIGNING_KEY`: Graceful Degradation — Gateway leitet alles durch

### Voraussetzungen

- **OpenResty** (statt nginx:alpine)
- **lua-resty-jwt** (installiert via `opm` im Dockerfile)
