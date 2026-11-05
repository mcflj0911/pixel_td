"""Test package. Puts the project folder on sys.path so the tests can import the game modules from anywhere."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# The tests place units at fixed cells on the first map, so they run with no doodads. test_world.py turns
# doodads back on for its own checks.
import world  # noqa: E402

world.DOODAD_DENSITY = 0.0
