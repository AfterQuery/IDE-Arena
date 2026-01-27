import subprocess
import sys
import pytest

def test_python_version():
    # Check Python 3.8+
    major, minor = sys.version_info[:2]
    assert (major, minor) >= (3, 8), f"Python >= 3.8 required, found {major}.{minor}"

# def test_required_commands():
#     # List of required commands
#     required = ["cmake", "make", "gcc", "g++", "pytest"]
#     for cmd in required:
#         result = subprocess.run(["which", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#         assert result.returncode == 0, f"Command not found: {cmd}"
