import pytest
import os

def test_folder_structure():
    """Verify the industrial MLOps directory structure exists."""
    required_dirs = ["src", "data", "deployments", "docs", "config", "experiments"]
    for d in required_dirs:
        assert os.path.isdir(d), f"Directory {d} is missing!"

def test_pipeline_import():
    """Verify that the pipeline script is present."""
    assert os.path.exists("src/pipeline.py")
