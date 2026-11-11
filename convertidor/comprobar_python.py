"""Sale con 0 si esta version de Python sirve para la app (3.10 a 3.14)."""
import sys

sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 14) else 1)
