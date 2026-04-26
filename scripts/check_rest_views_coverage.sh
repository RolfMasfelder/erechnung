#!/bin/bash
# Quick coverage check for api/rest_views.py

cd /app/project_root

echo "Running tests with coverage..."
COVERAGE_FILE=/tmp/.coverage coverage run --source='invoice_app' manage.py test invoice_app --verbosity=0

echo ""
echo "==================== COVERAGE REPORT FOR api/rest_views.py ===================="
COVERAGE_FILE=/tmp/.coverage coverage report --include='invoice_app/api/rest_views.py'

echo ""
echo "==================== TOTAL COVERAGE ===================="
COVERAGE_FILE=/tmp/.coverage coverage report | tail -1
