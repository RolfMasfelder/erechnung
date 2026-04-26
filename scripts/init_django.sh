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

echo "Django initialization complete!"
