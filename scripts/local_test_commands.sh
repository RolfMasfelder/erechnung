#!/bin/bash

# Individual Test Commands for Local Development
# Run these commands to replicate your GitHub CI locally

echo "🧪 Django eRechnung - Local Testing Commands"
echo "============================================"

# Check if Docker is running
if ! docker compose ps | grep -q "Up"; then
    echo "⚠️  Docker containers not running. Start with: ./start_app.sh"
    echo ""
fi

echo "📋 CODE QUALITY CHECKS:"
echo "  ./run_local_ci_checks.sh                          # Run all checks"
echo "  docker compose exec web ruff check project_root/          # Linting"
echo "  docker compose exec web ruff format --check project_root/ # Formatting"
echo "  docker compose exec web black --check project_root/       # Black formatting"
echo ""

echo "🔒 SECURITY CHECKS:"
echo "  docker compose exec web /home/appuser/.local/bin/pip-audit   # Python vulnerabilities"
echo "  trivy fs . (optional - install separately)                # Dependency scan"
echo ""

echo "🧪 APPLICATION TESTS:"
echo "  ./run_tests_docker.sh                                     # Your Django tests (87+)"
echo "  docker compose exec web python project_root/manage.py test --verbosity=2"
echo ""

echo "🐳 DOCKER TESTS:"
echo "  docker build -t test --target production .                # Test production build"
echo "  docker compose up -d --build                              # Test full stack"
echo ""

echo "📊 COVERAGE:"
echo "  docker compose exec web coverage run --source=invoice_app project_root/manage.py test"
echo "  docker compose exec web coverage report -m"
echo ""

echo "💡 TIP: Your pre-commit hooks already run ruff + black on commit!"
echo "💡 TIP: GitHub CI just adds security scanning and Docker builds"
