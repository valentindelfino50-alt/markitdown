"""Sale con 0 si esta Python sirve para la app: version 3.10 a 3.14 y de 64 bits."""
import struct
import sys

version = sys.version_info[:2]
bits = struct.calcsize("P") * 8
print(f"Python {version[0]}.{version[1]} de {bits} bits")

if not (3, 10) <= version <= (3, 14):
    print("  -> No sirve: hace falta la version 3.10 a 3.14 (recomendada: 3.13).")
    sys.exit(1)
if bits != 64:
    print("  -> No sirve: es de 32 bits y hace falta la de 64 bits.")
    sys.exit(1)
