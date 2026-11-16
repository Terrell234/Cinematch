#!/usr/bin/env bash
# Script to launch the CineMatch AI Modern Cinema Streamlit application

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR" || exit 1

echo "Starting CineMatch AI at http://localhost:8501"
if [ -x "$PROJECT_DIR/.venv/bin/streamlit" ]; then
    STREAMLIT_CONFIG_DIR="$PROJECT_DIR/.streamlit" \
    "$PROJECT_DIR/.venv/bin/streamlit" run app.py --server.port 8501
else
    streamlit run app.py --server.port 8501
fi
