"""
check_env.py — Verificación del entorno de PA Lab (Fase 0).

Uso (desde la raíz del repo, con el entorno virtual activado):
    python generator/check_env.py

Revisa:
  1. Versión de Python (mínimo 3.14; 3.13 se acepta como plan B con advertencia).
  2. Que se esté ejecutando dentro de un entorno virtual (.venv).
  3. Que las librerías de requirements.txt se importen y muestren su versión.
  4. Que existan las carpetas del repositorio definidas en ROADMAP.md.
  5. Que .gitignore excluya .venv/ y data/.

Termina con código 0 si todo está OK y 1 si hay algún error (útil para automatizar).
"""

from __future__ import annotations

import importlib
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PYTHON_MIN = (3, 14)
PYTHON_FALLBACK = (3, 13)

# nombre para importar -> nombre del paquete en pip
PACKAGES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "faker": "Faker",
}

EXPECTED_DIRS = ["docs", "generator", "api", "lake", "security", "data", "powerbi"]
GITIGNORE_RULES = [".venv/", "data/*"]


def ok(msg: str) -> None:
    print(f"  [OK]    {msg}")


def warn(msg: str) -> None:
    print(f"  [AVISO] {msg}")


def fail(msg: str) -> None:
    print(f"  [ERROR] {msg}")


def check_python() -> bool:
    print("\n1) Versión de Python")
    v = sys.version_info
    version = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= PYTHON_MIN:
        ok(f"Python {version}")
        return True
    if (v.major, v.minor) >= PYTHON_FALLBACK:
        warn(f"Python {version}: funciona como plan B, pero el roadmap asume 3.14")
        return True
    fail(f"Python {version}: se requiere 3.14 (o 3.13 como plan B)")
    return False


def check_venv() -> bool:
    print("\n2) Entorno virtual")
    in_venv = sys.prefix != sys.base_prefix
    if not in_venv:
        fail("No estás dentro de un entorno virtual. Activa .venv antes de correr esto.")
        return False
    venv_path = Path(sys.prefix).resolve()
    expected = (REPO_ROOT / ".venv").resolve()
    if venv_path == expected:
        ok(f"Entorno virtual del repo: {venv_path}")
    else:
        warn(f"Entorno virtual activo, pero no es el del repo: {venv_path}")
    return True


def check_packages() -> bool:
    print("\n3) Librerías")
    all_ok = True
    for import_name, dist_name in PACKAGES.items():
        try:
            importlib.import_module(import_name)
            ok(f"{dist_name} {metadata.version(dist_name)}")
        except Exception as exc:  # ImportError u otros errores de carga
            fail(f"{dist_name}: no se pudo importar ({exc.__class__.__name__}: {exc})")
            all_ok = False
    return all_ok


def check_dirs() -> bool:
    print("\n4) Estructura del repositorio")
    all_ok = True
    for d in EXPECTED_DIRS:
        if (REPO_ROOT / d).is_dir():
            ok(f"{d}/")
        else:
            fail(f"Falta la carpeta {d}/")
            all_ok = False
    return all_ok


def check_gitignore() -> bool:
    print("\n5) .gitignore")
    path = REPO_ROOT / ".gitignore"
    if not path.exists():
        fail("No existe .gitignore")
        return False
    lines = {line.strip() for line in path.read_text(encoding="utf-8").splitlines()}
    all_ok = True
    for rule in GITIGNORE_RULES:
        if rule in lines:
            ok(f"Regla presente: {rule}")
        else:
            fail(f"Falta la regla: {rule}")
            all_ok = False
    return all_ok


def main() -> int:
    print(f"PA Lab · verificación de entorno\nRepo: {REPO_ROOT}")
    results = [
        check_python(),
        check_venv(),
        check_packages(),
        check_dirs(),
        check_gitignore(),
    ]
    print()
    if all(results):
        print("RESULTADO: entorno listo ✔")
        return 0
    print("RESULTADO: hay errores; revisa las líneas [ERROR] ✘")
    return 1


if __name__ == "__main__":
    sys.exit(main())
