#!/bin/zsh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
  echo "Creating a local Python environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
if ! python -c "import streamlit, pandas, numpy, requests" >/dev/null 2>&1; then
  echo "Installing project dependencies..."
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

echo "Starting Personal Readiness Assistant..."
echo "Every product feature works with no API key; AI Coach explanations need DEEPSEEK_API_KEY."
echo "Press Control + C in this window to stop."
python -m streamlit run app.py
