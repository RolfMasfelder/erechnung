#!/bin/bash

# Run Django tests with coverage
# This script runs all tests and generates a coverage report
# It can run tests locally or inside a Docker container

set -e

# Parse command line arguments
USE_DOCKER=false
while getopts ":d" opt; do
  case $opt in
    d)
      USE_DOCKER=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Function to run tests in Docker
run_in_docker() {
    echo "Running tests in Docker container..."
    cd "$(dirname "$0")"/../../..  # Navigate to the project root where docker-compose.yml is located

    # Run tests with coverage inside the running web container
    # /tmp for .coverage data (avoid permission issues), /app/htmlcov for HTML output (mounted volume)
    docker compose exec web sh -c "
        cd project_root &&
        COVERAGE_FILE=/tmp/.coverage coverage run --source='invoice_app' manage.py test invoice_app &&
        COVERAGE_FILE=/tmp/.coverage coverage report -m &&
        COVERAGE_FILE=/tmp/.coverage coverage html --directory=/app/htmlcov
    "

    # Fix ownership so the host user can read the generated files
    sudo chown -R "$(id -un):$(id -gn)" htmlcov/ 2>/dev/null || true

    # Copy HTML report from container to host workspace
    docker compose cp web:/app/htmlcov/. htmlcov/

    echo ""
    echo "HTML coverage report: htmlcov/index.html"
}

# Function to run tests locally
run_locally() {
    echo "Running tests locally..."

    # Change to the Django project directory
    cd "$(dirname "$0")/../project_root"

    # Activate virtual environment if needed (uncomment if using a virtualenv)
    # source ../venv/bin/activate

    # Install coverage if not already installed
    pip install coverage

    # Run tests with coverage
    coverage run --source='invoice_app' manage.py test invoice_app

    # Generate coverage report
    coverage report -m

    # Generate HTML report
    coverage html

    echo "Coverage report generated in htmlcov/ directory"
    echo "Open htmlcov/index.html in a browser to view the report"
}

# Run in Docker or locally based on the flag
if [ "$USE_DOCKER" = true ]; then
    run_in_docker
else
    run_locally
fi
