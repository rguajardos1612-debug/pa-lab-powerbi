"""
reproducibilidad.py — Prueba de D-003: misma semilla + mismo código = mismos datos.

Uso (desde la raíz del repo, con .venv activado):
    python generator/reproducibilidad.py

Corre generar.py dos veces, cada una con un PYTHONHASHSEED distinto (el valor que
Python usa para ordenar internamente los textos dentro de un set). Si alguna tabla
cambia entre las dos ejecuciones, el generador depende de algo que no es la semilla.
Termina con código 0 si las 15 tablas son idénticas y 1 si alguna difiere.

Origen: S3. Un sorted(set(...)) con empates hacía que las promociones de Perú
cambiaran en cada ejecución (ver D-021).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "csv"
GENERADOR = RAIZ / "generator" / "generar.py"
SEMILLAS_HASH = ("1", "2")


def huellas() -> dict[str, str]:
    """Hash SHA-256 de cada CSV generado."""
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(CSV.glob("*.csv"))}


def ejecutar(semilla_hash: str) -> dict[str, str]:
    # PYTHONIOENCODING: en Windows, la salida capturada usa cp1252 y no puede escribir
    # caracteres como "←"; generar.py fallaría al imprimir su resumen.
    entorno = {**os.environ, "PYTHONHASHSEED": semilla_hash, "PYTHONIOENCODING": "utf-8"}
    print(f"  Ejecutando generar.py con PYTHONHASHSEED={semilla_hash} ...", flush=True)
    resultado = subprocess.run([sys.executable, str(GENERADOR)], env=entorno,
                               capture_output=True, text=True, encoding="utf-8")
    if resultado.returncode != 0:
        print(resultado.stdout, resultado.stderr)
        raise SystemExit("generar.py terminó con error")
    return huellas()


def main() -> int:
    print("PA Lab · prueba de reproducibilidad (D-003, D-021)")
    a = ejecutar(SEMILLAS_HASH[0])
    b = ejecutar(SEMILLAS_HASH[1])
    distintas = [n for n in a if a[n] != b.get(n)]
    if set(a) != set(b):
        distintas.append("(no se generaron las mismas tablas)")
    print()
    if distintas:
        print(f"NO REPRODUCIBLE ✘ · {len(distintas)} tabla(s) cambian entre ejecuciones:")
        for n in distintas:
            print(f"  [DIFIERE] {n}")
        return 1
    print(f"REPRODUCIBLE ✔ · {len(a)} tablas idénticas en las dos ejecuciones")
    print(f"  Huella de EmpJob.csv: {a['EmpJob.csv'][:16]}…")
    return 0


if __name__ == "__main__":
    sys.exit(main())
