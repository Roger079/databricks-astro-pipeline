"""Compatibility entry point for the current normalized demo evidence."""
from pathlib import Path
import runpy
import sys
if '--kind' not in sys.argv:
    sys.argv += ['--kind', 'demo']
if '--schema' not in sys.argv:
    sys.argv += ['--schema', 'astro_taco_main_demo']
runpy.run_path(str(Path(__file__).with_name('capture_run_evidence.py')), run_name='__main__')
