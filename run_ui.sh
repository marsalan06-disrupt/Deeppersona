#!/bin/bash
# Launch Deeppersona UI

cd "$(dirname "$0")"

echo "Starting Deeppersona UI..."
echo "Open http://localhost:8501 in your browser"
echo ""

streamlit run ui/app.py --server.headless true
