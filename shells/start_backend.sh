#!/bin/bash
cd "$(dirname "$0")/.."
conda activate yuexia
python -m src.backend.app
