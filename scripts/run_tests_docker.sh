#!/bin/bash

# Run tests with Docker
# This is a shortcut script to run the tests with Docker

set -e

# Navigate to the test directory
cd "$(dirname "$0")/../project_root/invoice_app/tests"

# Run the test script with the Docker flag
./run_tests_with_coverage.sh -d
