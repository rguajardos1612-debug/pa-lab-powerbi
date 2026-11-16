"""
sabotaje.py — Prueba del validador: ¿detecta errores plantados a propósito? (S3, Ejercicio 4)

Uso (desde la raíz del repo, con .venv activado, después de generar.py):
    python generator/sabotaje.py

Para cada sabotaje: copia las tablas en memoria, rompe UNA cosa, corre las mismas
pruebas de validar.py y muestra qué falló. Los archivos de data/ no se modifican.
Un validador que no detecta un sabotaje tiene un punto ciego.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validar as V  # noqa: E402

TABLAS = ["EmpJob", "EmpEmployment", "EmpEmploymentTermination", "EmpPayCompRecurring", "PerPerson",
          "PerPersonal", "PerNationalId", "FOLocation", "FOEventReason", "FOCompany", "FOJobCode",
          "FODepartment", "FODivision", "FOBusinessUnit"]


def fallas(t: dict) -> list[tuple[str, str]]:
    inf = V.Informe()
    V.reglas(t, inf)
    V.valores(t, inf)
    return [(n, o) for n, _, o, s in inf.filas if s != "OK"]


def copia(base: dict) -> dict:
    return {k: v.copy() for k, v in base.items()}


def mover_fecha(df, fila, col, dias):
    df.at[fila, col] = df.at[fila, col] + timedelta(days=dias)
    df.at[fila, col + "_o"] = df.at[fila, col].toordinal()


def s1(t):
    job = t["EmpJob"]
    f = job[(job["eventReason"] == "TER_FIN_OBRA") & (job["startDate"].map(lambda d: d.year) == 2025)].index[0]
    job.at[f, "emplStatus"] = "A"
    return f"EmpJob {job.at[f, 'userId']}: TERMINATION (TER_FIN_OBRA, {job.at[f, 'startDate']}) con emplStatus A"


def s2(t):
    job = t["EmpJob"]
    f = job[(job["event"] == "PROMOTION") & (job["startDate"].map(lambda d: d.year) == 2025)].index[0]
    mover_fecha(job, f, "startDate", 1)
    return f"EmpJob {job.at[f, 'userId']}: PROMOTION movida de {job.at[f, 'startDate'] - timedelta(days=1)} a {job.at[f, 'startDate']}"


def s3(t):
    job, emp = t["EmpJob"], t["EmpEmployment"]
    u = job.loc[job["event"] == "REHIRE", "userId"].iloc[0]
    f = emp[emp["userId"] == u].index[0]
    emp.at[f, "personIdExternal"] = "P9999999"
    return f"EmpEmployment {u} (REHIRE) reasignado a P9999999, que no existe"


def s4(t):
    nid = t["PerNationalId"]
    chl = nid[nid["country"] == "CHL"].index
    nid.at[chl[1], "nationalId"] = nid.at[chl[0], "nationalId"]
    return f"PerNationalId: {nid.at[chl[1], 'personIdExternal']} recibe el documento de {nid.at[chl[0], 'personIdExternal']}"


def main() -> int:
    base = {n: V.leer(n) for n in TABLAS}
    print("PA Lab · prueba del validador con sabotajes")
    limpio = fallas(copia(base))
    print(f"\n0. Sin sabotaje: {len(limpio)} falla(s)" + ("" if not limpio else f" → {limpio}"))
    ciegos = 0
    for k, sabotaje in enumerate((s1, s2, s3, s4), start=1):
        t = copia(base)
        descripcion = sabotaje(t)
        resultado = fallas(t)
        print(f"\n{k}. {descripcion}")
        if not resultado:
            ciegos += 1
            print("   ✘ NO DETECTADO (punto ciego del validador)")
        for nombre, obtenido in resultado:
            print(f"   ✔ {nombre}: {obtenido}")
    print(f"\n{'VALIDADOR SIN PUNTOS CIEGOS EN ESTOS 4 CASOS ✔' if ciegos == 0 else f'{ciegos} SABOTAJE(S) NO DETECTADO(S) ✘'}")
    return 0 if ciegos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
