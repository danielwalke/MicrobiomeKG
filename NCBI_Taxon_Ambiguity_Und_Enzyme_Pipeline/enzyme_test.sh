#!/usr/bin/env bash
set -e

cd /home/benjamin.reyes/git/MicrobiomeKG

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r /home/benjamin.reyes/git/MicrobiomeKG/requirements.txt

export PYTHONPATH="$PWD"
export NEO4J_URI="bolt://172.31.151.160:8085"
export NEO4J_URL="$NEO4J_URI"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD=""

python benjas_shit/main_test.py