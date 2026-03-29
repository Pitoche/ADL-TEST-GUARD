#!/bin/bash
cd /home/kali/ADL-TEST-GUARD || exit 1

echo "Cleaning cache..."
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "Running tests..."
/home/kali/ADL-TEST-GUARD/venv/bin/pytest -v -s testing/pytest || exit 1

echo "Starting app..."
/home/kali/ADL-TEST-GUARD/venv/bin/python run.py
