"""Permite ejecutar las pruebas desde la carpeta del proyecto o su padre."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
