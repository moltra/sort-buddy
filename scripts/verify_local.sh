#!/bin/bash
set -e

echo "=== Running local verification pipeline ==="
echo ""

echo "1. Installing dependencies with Poetry..."
poetry install --no-root

echo ""
echo "2. Running deptry..."
poetry run deptry . --per-rule-ignores 'DEP001=ai|config|email_clients|accounts_config|account_processor|email_fetcher|json_email_fetcher|util'

echo ""
echo "3. Running mypy..."
poetry run mypy --strict src/

echo ""
echo "4. Running pytest (excluding live tests)..."
poetry run pytest -o addopts='--no-header -q --cov=src --cov-report=term-missing' tests/unit/ tests/integration/ -m 'not live'

echo ""
echo "=== All checks passed! ==="
