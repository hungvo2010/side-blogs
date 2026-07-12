#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    cp .env.example .env
    exit 1
fi

if [ ! -d .venv ]; then
    exit 1
fi

source .venv/bin/activate
streamlit run streamlit_app/app.py --server.port 8501 --server.headless true

