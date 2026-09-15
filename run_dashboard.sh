#!/bin/bash
# Runs the Phase 6 dashboard using the existing SSS virtual environment

echo "Starting Ghost-Net Sonar Analytics Dashboard (v2)..."
/home/tharoon/projects/Nexus/venv/bin/streamlit run app.py --server.port 8502 --server.fileWatcherType none
