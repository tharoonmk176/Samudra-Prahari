#!/bin/bash
set -e

echo "=== Phase 1: Data + Training Setup ==="

# 1. Install dependencies
echo "Installing dependencies..."
./venv/bin/pip install ultralytics pyyaml

# 2. Clone the repository if it doesn't exist
if [ ! -d "SCTD" ]; then
    echo "Cloning SCTD dataset..."
    git clone https://github.com/freepoet/SCTD.git
    
    # 3. Unzip the dataset
    echo "Unzipping SCTD dataset..."
    cd SCTD
    unzip -q SCTD.zip
    cd ..
else
    echo "SCTD directory already exists. Skipping clone."
fi

# 4. Run voc2yolo.py conversion
echo "Running VOC to YOLO conversion..."
./venv/bin/python voc2yolo.py

# 5. Run YOLO training
echo "Starting YOLO training..."
# NOTE: If you are not on a GPU, this will fail or run very slowly on CPU.
# In a Colab environment, ensure the runtime is set to T4 GPU.
./venv/bin/python train_yolo.py

echo "=== Phase 1 Execution Complete ==="
