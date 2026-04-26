FROM postgres:17

# Install pgTAP and additional useful extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-17-pgtap \
    && rm -rf /var/lib/apt/lists/*

# Copy init script to enable extensions on DB creation
COPY init-extensions.sql /docker-entrypoint-initdb.d/01-extensions.sql

# Copy TLS entrypoint wrapper (copies certs with correct permissions)
COPY docker-entrypoint-tls.sh /usr/local/bin/docker-entrypoint-tls.sh
RUN chmod +x /usr/local/bin/docker-entrypoint-tls.sh

ENTRYPOINT ["docker-entrypoint-tls.sh"]
