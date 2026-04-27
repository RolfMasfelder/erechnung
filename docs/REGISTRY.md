# Private Docker Registry (192.168.178.80:5000)

## Übersicht

Private Docker Registry v2 auf dem k3s-Server (`cirrus7-neu` / `192.168.178.80`).
Dient als Image-Quelle für den k3s-Cluster. Alle selbst gebauten Images werden hier mit
versionierten Tags (`v<version>-<git-sha>`) abgelegt.

**Regel: Kein `:latest`-Tag.** Alle Images verwenden explizite Versionen.

## Start-Befehl

```bash
docker run -d \
  --name registry \
  --restart=always \
  -p 5000:5000 \
  -v registry-data:/var/lib/registry \
  -v /home/rolf/workspace/erechnung/infra/api-gateway/certs:/certs \
  -e REGISTRY_HTTP_TLS_CERTIFICATE=/certs/localhost.crt \
  -e REGISTRY_HTTP_TLS_KEY=/certs/localhost.key \
  -e REGISTRY_STORAGE_DELETE_ENABLED=true \
  registry:2
```

## Konfiguration

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| Image | `registry:2` | Docker Registry v2 |
| Port | `5000` → `5000` | HTTPS (TLS) |
| Restart | `always` | Automatischer Neustart |
| TLS-Zertifikat | `/certs/localhost.crt` | Selbstsigniertes Zertifikat |
| TLS-Key | `/certs/localhost.key` | Privater Schlüssel |
| Delete | `true` | Manifest-Löschungen erlaubt |
| Daten-Volume | `registry-data` → `/var/lib/registry` | Persistenter Speicher |
| Cert-Mount | `.../api-gateway/certs` → `/certs` | TLS-Zertifikate vom Host |

## Gespeicherte Images

Selbst gebaut (versioniert via `kustomization.yaml`):

- `erechnung-web`
- `erechnung-init`
- `erechnung-celery`
- `erechnung-frontend`
- `erechnung-api-gateway`
- `erechnung-postgres`

Extern (feste Versionen):

- `redis:7-alpine`
- `busybox:1.35`

## Tagging-Schema

Tags werden automatisch durch `scripts/k3s-update-images.sh` erzeugt:

```
v<version>-<git-sha>
```

- `<version>`: aus `pyproject.toml` (`version = "1.0.0"`)
- `<git-sha>`: `git rev-parse --short HEAD`
- Beispiel: `v1.0.0-b9a325d`

Die aktiven Tags stehen in `infra/k8s/k3s/kustomization.yaml` unter `images:`.

## Nützliche Befehle

```bash
# Katalog anzeigen
curl -sk https://192.168.178.80:5000/v2/_catalog

# Tags eines Images auflisten
curl -sk https://192.168.178.80:5000/v2/erechnung-web/tags/list

# Alle Images bauen, taggen, pushen und deployen
cd scripts && ./k3s-update-images.sh

# Nur pushen ohne Neubau
cd scripts && ./k3s-update-images.sh --skip-build
```

## k3s Registry-Konfiguration

k3s muss die private Registry als "insecure" (selbstsigniertes Zertifikat) kennen.
Konfiguration auf dem Server unter `/etc/rancher/k3s/registries.yaml`:

```yaml
mirrors:
  "192.168.178.80:5000":
    endpoint:
      - "https://192.168.178.80:5000"
configs:
  "192.168.178.80:5000":
    tls:
      insecure_skip_verify: true
```
