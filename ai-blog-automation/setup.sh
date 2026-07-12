#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    cp .env.example .env
    exit 1
fi

python3 -m venv .venv
source .venv/bin/activate
pip install -e .

alembic upgrade head
