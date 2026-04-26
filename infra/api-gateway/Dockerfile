# API Gateway for eRechnung Django App
# Uses OpenResty (nginx + Lua) for perimeter JWT validation (Defense-in-Depth)

FROM openresty/openresty:alpine

# Install lua-resty-jwt for JWT validation at the gateway
RUN apk add --no-cache perl curl \
    && opm get SkyLothar/lua-resty-jwt

# Copy nginx configuration
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY api-gateway-https.conf /etc/nginx/conf.d/default.conf

# Copy SSL certificates
COPY certs/localhost.crt /etc/nginx/certs/localhost.crt
COPY certs/localhost.key /etc/nginx/certs/localhost.key

# Copy Lua scripts for JWT validation
COPY lua/ /etc/nginx/lua/

# Create directories for logs and temp files
RUN mkdir -p /var/log/nginx/api-gateway \
    && mkdir -p /tmp/nginx \
    && mkdir -p /etc/nginx/certs

# Health check endpoint
COPY healthcheck.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/healthcheck.sh

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
