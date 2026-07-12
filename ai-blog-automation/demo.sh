#!/bin/bash
set -e

./start.sh --remove-orphans
docker-compose exec -T app python scripts/seed_demo.py
docker-compose exec -T app python scripts/export_static.py 1

