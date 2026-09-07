#!/bin/bash
# Installs streamlit and runs the Phase 6 dashboard

echo "Installing Streamlit and Pandas..."
./venv/bin/pip install streamlit pandas

echo "Starting Ghost-Net Sonar Analytics Dashboard..."
./venv/bin/streamlit run app.py --server.fileWatcherType none
