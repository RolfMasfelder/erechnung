#!/bin/bash
set -e

echo "Running Django initialization..."

echo "1. Running migrations..."
python project_root/manage.py migrate

echo "2. Collecting static files..."
python project_root/manage.py collectstatic --no-input

echo "3. Creating superuser if needed..."
python project_root/manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()

# Create superuser for admin access
if not User.objects.filter(username="admin").exists():
    User.objects.create_superuser("admin", "admin@example.com", "admin")
    print("Superuser created: admin/admin")
else:
    print("Superuser already exists")

# Create test user for E2E tests
if not User.objects.filter(username="testuser").exists():
    User.objects.create_user("testuser", "test@example.com", "testpass123")
    print("Test user created: testuser/testpass123")
else:
    print("Test user already exists")
EOF

echo "4. Generating test data if needed..."
if [ "${INIT_CREATE_TEST_DATA:-true}" = "true" ]; then
    INVOICE_COUNT=$(python project_root/manage.py shell -c "from invoice_app.models import Invoice; print(Invoice.objects.count())" 2>/dev/null | tail -1)
    if [ "$INVOICE_COUNT" = "0" ]; then
        echo "No invoices found - generating test data (INIT_CREATE_TEST_DATA=true)..."
        python project_root/manage.py generate_test_data --preset standard
    else
        echo "Test data already present ($INVOICE_COUNT invoices) - skipping generation"
    fi
else
    echo "Skipping test data bootstrap (INIT_CREATE_TEST_DATA=false)"
fi

echo "Django initialization complete!"
