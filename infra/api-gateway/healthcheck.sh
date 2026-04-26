#!/bin/sh
# API Gateway Health Check Script
#
# Checks both nginx process health and the gateway-health endpoint.
# Used by Docker HEALTHCHECK and monitoring systems.

# Check if nginx/openresty master process is running
if ! pgrep -f "nginx: master" > /dev/null 2>&1; then
    echo "ERROR: nginx/openresty is not running"
    exit 1
fi

# Check gateway-health endpoint (nginx-level, no backend dependency)
# Try HTTPS first (production), fall back to HTTP (development/k8s)
if curl -sf --max-time 2 https://localhost/gateway-health -k >/dev/null 2>&1; then
    echo "OK: API Gateway is healthy (HTTPS)"
    exit 0
elif curl -sf --max-time 2 http://localhost:8080/gateway-health >/dev/null 2>&1; then
    echo "OK: API Gateway is healthy (HTTP)"
    exit 0
fi

echo "ERROR: gateway-health endpoint not responding"
exit 1
