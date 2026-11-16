"""
validar.py — Validación de los datos generados (Fase 1, paso 8 del diseño).

Uso (desde la raíz del repo, con .venv activado, después de generar.py):
    python generator/validar.py

Revisa dos cosas:
  A. Las 11 reglas de docs/diccionario_datos.md §8 (más integridad con los catálogos).
     Son reglas EXACTAS: una sola fila que no cumple es un error.
  B. Los valores esperados de docs/diseno_generador.md §3. Son estimaciones de flujo:
     se comparan con una tolerancia y algunas solo generan un aviso.

Estados: OK · ERROR (regla rota o valor fuera de tolerancia) · AVISO (informativo).
Termina con código 0 si no hay errores y 1 si hay alguno.
"""

from __future__ import annotations

import re
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

DATOS = Path(__file__).resolve().parent.parent / "data" / "parquet"
FIN = C.IDS.fecha_abierta.toordinal()

# Ventana de análisis (D-010): 2023-11-01 a 2026-10-31
D0 = C.PERIODO.primer_mes
_k = D0.year * 12 + D0.month - 1 + C.PERIODO.meses
D1 = date(_k // 12, _k % 12 + 1, 1) - timedelta(days=1)
MESES = C.PERIODO.meses


def cierres() -> list[int]:
    """Último día de cada mes de la ventana, como número de día (ordinal)."""
    res = []
    for i in range(1, MESES + 1):
        k = D0.year * 12 + D0.month - 1 + i
        res.append((date(k // 12, k % 12 + 1, 1) - timedelta(days=1)).toordinal())
    return res


# ─────────────────────────────────────────────────────────────────────────────
# Lectura: las fechas se pasan a ordinales (enteros) para comparar rápido y sin
# problemas con 9999-12-31, que no cabe en un datetime de pandas.
# ─────────────────────────────────────────────────────────────────────────────
def leer(nombre: str) -> pd.DataFrame:
    tabla = pq.read_table(DATOS / f"{nombre}.parquet")
    df = tabla.to_pandas(date_as_object=True)
    for campo in tabla.schema:
        if pa.types.is_date(campo.type):     # el tipo lo dice el archivo, no se adivina
            df[campo.name + "_o"] = [d.toordinal() if isinstance(d, date) else -1 for d in df[campo.name]]
    return df


class Informe:
    def __init__(self) -> None:
        self.filas: list[tuple[str, str, str, str]] = []

    def regla(self, nombre: str, malos: int, detalle: str = "") -> None:
        estado = "OK" if malos == 0 else "ERROR"
        self.filas.append((nombre, "0 filas", f"{malos:,} filas".replace(",", ".") + detalle, estado))

    def valor(self, nombre: str, esperado: str, obtenido: str, ok: bool, solo_aviso: bool = False) -> None:
        estado = "OK" if ok else ("AVISO" if solo_aviso else "ERROR")
        self.filas.append((nombre, esperado, obtenido, estado))

    def imprimir(self, titulo: str) -> None:
        print(f"\n{titulo}")
        print(f"  {'Indicador':<64}{'Esperado':<26}{'Obtenido':<16}Estado")
        for n, e, o, s in self.filas:
            print(f"  {n[:63]:<64}{e:<26}{o:<16}{s}")
        self.filas_previas = getattr(self, "filas_previas", []) + self.filas
        self.filas = []

    def errores(self) -> int:
        return sum(1 for f in getattr(self, "filas_previas", []) if f[3] == "ERROR")

    def avisos(self) -> int:
        return sum(1 for f in getattr(self, "filas_previas", []) if f[3] == "AVISO")


def pct(x: float) -> str:
    return f"{x * 100:.1f} %".replace(".", ",")


def num(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ─────────────────────────────────────────────────────────────────────────────
# A. Reglas exactas del diccionario (§8)
# ─────────────────────────────────────────────────────────────────────────────
def vigencias_continuas(df: pd.DataFrame, fin_ultima: pd.Series) -> int:
    """Cuenta filas que rompen la continuidad: cada fila debe terminar el día antes de
    la siguiente y la última debe terminar en fin_ultima (por userId)."""
    df = df.sort_values(["userId", "startDate_o"])
    siguiente = df.groupby("userId")["startDate_o"].shift(-1)
    hay_sig = siguiente.notna()
    malos = (hay_sig & (df["endDate_o"] != siguiente - 1)).sum()
    ultima = ~hay_sig
    esperado = df.loc[ultima, "userId"].map(fin_ultima)
    malos += (df.loc[ultima, "endDate_o"] != esperado).sum()
    malos += (df["endDate_o"] < df["startDate_o"]).sum()
    return int(malos)


def reglas(t: dict[str, pd.DataFrame], inf: Informe) -> None:
    job, emp, ter, pay = t["EmpJob"], t["EmpEmployment"], t["EmpEmploymentTermination"], t["EmpPayCompRecurring"]
    per, nid, loc, motivo = t["PerPerson"], t["PerNationalId"], t["FOLocation"], t["FOEventReason"]

    # 1. Integridad referencial (más catálogos)
    malos = (~job["userId"].isin(emp["userId"])).sum() + (~emp["personIdExternal"].isin(per["personIdExternal"])).sum()
    for col, cat, llave in [("eventReason", "FOEventReason", "externalCode"), ("location", "FOLocation", "externalCode"),
                            ("jobCode", "FOJobCode", "externalCode"), ("company", "FOCompany", "externalCode"),
                            ("department", "FODepartment", "externalCode"), ("division", "FODivision", "externalCode"),
                            ("businessUnit", "FOBusinessUnit", "externalCode")]:
        malos += (~job[col].isin(t[cat][llave])).sum()
    estado_de = dict(zip(motivo["externalCode"], motivo["emplStatus"]))
    malos += (job["emplStatus"] != job["eventReason"].map(estado_de)).sum()
    inf.regla("R1  Integridad referencial y catálogos", int(malos))

    # 2. Sin solapamientos ni huecos (EmpJob hasta 9999; pagos hasta el fin del empleo)
    fin_empleo = emp.set_index("userId")["endDate_o"]
    malos = vigencias_continuas(job, pd.Series(FIN, index=fin_empleo.index))
    malos += vigencias_continuas(pay, fin_empleo)
    primera_pago = pay.sort_values("startDate_o").groupby("userId")["startDate_o"].first()
    malos += int((primera_pago != emp.set_index("userId")["startDate_o"].reindex(primera_pago.index)).sum())
    inf.regla("R2  Vigencias continuas (EmpJob y pagos)", malos)

    # 3. Primera fila: HIRE o REHIRE con startDate = inicio del empleo
    primera = job.sort_values(["userId", "startDate_o"]).groupby("userId").first()
    inicio = emp.set_index("userId")["startDate_o"]
    malos = (~primera["event"].isin(["HIRE", "REHIRE"])).sum()
    malos += (primera["startDate_o"] != inicio.reindex(primera.index)).sum()
    inf.regla("R3  Primera fila HIRE/REHIRE en el inicio", int(malos))

    # 4. REHIRE si y solo si la persona ya tuvo un empleo anterior
    orden = emp.sort_values(["personIdExternal", "startDate_o"]).copy()
    orden["n"] = orden.groupby("personIdExternal").cumcount()
    es_rehire = orden["userId"].map(primera["event"]) == "REHIRE"
    malos = (es_rehire != (orden["n"] > 0)).sum()
    malos += (orden["originalStartDate_o"] != orden.groupby("personIdExternal")["startDate_o"].transform("min")).sum()
    inf.regla("R4  REHIRE ⇔ empleo anterior (y originalStartDate)", int(malos))

    # 5. Terminados: fila TERMINATION el día siguiente y fila en EmpEmploymentTermination
    cerrados = emp[emp["endDate_o"] != FIN]
    term = job[job["event"] == "TERMINATION"].set_index("userId")["startDate_o"]
    malos = (term.reindex(cerrados["userId"]).to_numpy() != cerrados["endDate_o"].to_numpy() + 1).sum()
    malos += len(set(term.index) - set(cerrados["userId"])) + term.index.duplicated().sum()
    t_fin = ter.set_index("userId")["endDate_o"]
    malos += (t_fin.reindex(cerrados["userId"]).to_numpy() != cerrados["endDate_o"].to_numpy()).sum()
    malos += len(ter) - len(cerrados)
    inf.regla("R5  Términos completos (D-008)", int(malos))

    # 6. Una persona no tiene dos empleos activos el mismo día
    sig = orden.groupby("personIdExternal")["startDate_o"].shift(-1)
    malos = (sig.notna() & (sig <= orden["endDate_o"])).sum()
    inf.regla("R6  Sin empleos simultáneos", int(malos))

    # 7. Moneda del pago = moneda de la compañía
    moneda = dict(zip(t["FOCompany"]["externalCode"], t["FOCompany"]["currency"]))
    malos = job.groupby("userId")["company"].nunique().gt(1).sum()
    malos += (pay["currencyCode"] != pay["userId"].map(primera["company"].map(moneda))).sum()
    inf.regla("R7  Moneda coherente con la compañía", int(malos))

    # 8. Nadie trabaja en una obra fuera de sus fechas (filas activas)
    obras = loc[loc["cust_tipo"] == "OBRA"].set_index("externalCode")
    act = job[(job["emplStatus"] == "A") & job["location"].isin(obras.index)]
    ini_o = act["location"].map(obras["cust_obraInicio_o"])
    fin_o = act["location"].map(obras["cust_obraFin_o"])
    # 9999-12-31 significa "vigente, sin fecha de fin conocida", no "trabaja hasta 9999".
    # Por eso el fin de la fila se acota a la fecha de corte de los datos (fin de la ventana):
    # una obra que termina en 2027 tiene gente vigente hoy con endDate abierto.
    fin_fila = np.minimum(np.minimum(act["endDate_o"], act["userId"].map(fin_empleo)), D1.toordinal())
    malos = ((act["startDate_o"] < ini_o) | (fin_fila > fin_o)).sum()
    inf.regla("R8  Trabajo dentro de las fechas de la obra", int(malos))

    # 9. nationalId ficticio, con formato correcto y sin repetir (D-007)
    pc, pp, n = C.IDS.prefijo_doc["CHL"], C.IDS.prefijo_doc["PER"], C.IDS.digitos_doc
    patron = {"CHL": re.compile(rf"^{pc}(\d{{{n}}})-([0-9K])$"), "PER": re.compile(rf"^{pp}\d{{{n}}}$")}
    malos = 0
    for pais, doc in zip(nid["country"], nid["nationalId"]):
        m = patron[pais].match(doc)
        if not m:
            malos += 1
        elif pais == "CHL" and m.group(2) != digito_verificador(m.group(1)):
            malos += 1
    malos += nid["nationalId"].duplicated().sum()
    inf.regla("R9  nationalId ficticio, válido y único", int(malos))

    # 10. Motivos de pago válidos; cada PRO_PROM tiene su promoción en EmpJob
    validos = set(motivo.loc[motivo["event"].isin(["HIRE", "REHIRE", "PAY_CHANGE", "PROMOTION"]), "externalCode"])
    malos = (~pay["eventReason"].isin(validos)).sum()
    prom_job = set(zip(job.loc[job["event"] == "PROMOTION", "userId"], job.loc[job["event"] == "PROMOTION", "startDate_o"]))
    prom_pay = pay[pay["eventReason"] == "PRO_PROM"]
    malos += sum((u, d) not in prom_job for u, d in zip(prom_pay["userId"], prom_pay["startDate_o"]))
    inf.regla("R10 Motivos de pago y promociones", int(malos))
    # La regla 11 (dotación y 75/25) se revisa en la parte B.


def digito_verificador(numero: str) -> str:
    suma, factor = 0, 2
    for d in reversed(numero):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


# ─────────────────────────────────────────────────────────────────────────────
# B. Valores esperados (diseño §3)
# ─────────────────────────────────────────────────────────────────────────────
def valores(t: dict[str, pd.DataFrame], inf: Informe) -> None:
    job, emp, ter, pay = t["EmpJob"], t["EmpEmployment"], t["EmpEmploymentTermination"], t["EmpPayCompRecurring"]
    d0, d1 = D0.toordinal(), D1.toordinal()
    primera = job.sort_values(["userId", "startDate_o"]).groupby("userId").first()
    clase = primera["employeeClass"]
    pais = primera["company"].map(dict(zip(t["FOCompany"]["externalCode"], t["FOCompany"]["country"])))
    emp = emp.assign(clase=emp["userId"].map(clase), pais=emp["userId"].map(pais))
    ter = ter.assign(clase=ter["userId"].map(clase),
                     inicio=ter["userId"].map(emp.set_index("userId")["startDate_o"]))
    activa = job[job["emplStatus"] == "A"]
    a_ini, a_fin = activa["startDate_o"].to_numpy(), activa["endDate_o"].to_numpy()
    a_clase = activa["employeeClass"].to_numpy()
    a_pais = activa["userId"].map(pais).to_numpy()
    a_inicio_emp = activa["userId"].map(emp.set_index("userId")["startDate_o"]).to_numpy()

    def stock(dia: int) -> np.ndarray:
        return (a_ini <= dia) & (dia <= a_fin)

    # Dotación de cierre (regla de dotación del diccionario §1)
    serie, chl, emp_c, emp_nuevos = [], [], [], []
    for dia in cierres():
        m = stock(dia)
        serie.append(m.sum())
        chl.append((m & (a_pais == "CHL")).sum())
        emp_c.append((m & (a_clase == "EMP")).sum())
        emp_nuevos.append((m & (a_clase == "EMP") & (dia - a_inicio_emp < 365.25)).sum())
    serie, chl, emp_c, emp_nuevos = map(np.asarray, (serie, chl, emp_c, emp_nuevos))
    obj, osc = C.DOTACION.promedio_cierre_mes, C.DOTACION.oscilacion
    prom = serie.mean()
    inf.valor("Dotación promedio de cierre", f"{num(obj)} ±3 %", num(prom),
              abs(prom / obj - 1) <= C.DOTACION.tolerancia_promedio)
    lo, hi = obj * (1 - osc), obj * (1 + osc)
    inf.valor("Dotación mínima y máxima", f"{num(lo)} / {num(hi)} ±5 %", f"{num(serie.min())} / {num(serie.max())}",
              abs(serie.min() / lo - 1) <= 0.05 and abs(serie.max() / hi - 1) <= 0.05)
    p_chl = chl.sum() / serie.sum()
    inf.valor("Chile / Perú", "75 / 25 ±2 pp", f"{p_chl * 100:.1f} / {(1 - p_chl) * 100:.1f}".replace(".", ","),
              abs(p_chl - C.DOTACION.participacion_pais["CHL"]) <= 0.02)
    p_obr = 1 - emp_c.sum() / serie.sum()
    inf.valor("Obreros / Empleados", "70 / 30 ±2 pp", f"{p_obr * 100:.1f} / {(1 - p_obr) * 100:.1f}".replace(".", ","),
              abs(p_obr - C.DOTACION.participacion_clase["OBR"]) <= 0.02)

    # Empleados
    en_ventana = lambda col: (col >= d0) & (col <= d1)  # noqa: E731
    ing_emp = (en_ventana(emp["startDate_o"]) & (emp["clase"] == "EMP")).sum() / MESES
    inf.valor("EMP: ingresos al mes", "≈37 (30–45)", num(ing_emp, 1), 30 <= ing_emp <= 45)
    ter_v = ter[en_ventana(ter["endDate_o"])]
    t_emp = ter_v[ter_v["clase"] == "EMP"]
    rot_emp = len(t_emp) / emp_c.mean() / (MESES / 12)
    inf.valor("EMP: rotación anual", "≈15 % (12–18 %)", pct(rot_emp), 0.12 <= rot_emp <= 0.18)
    nuevos = emp_nuevos.sum() / emp_c.sum()
    inf.valor("EMP: proporción con ≤12 meses", "≈13 % (10–17 %)", pct(nuevos), 0.10 <= nuevos <= 0.17)
    ren = t_emp[t_emp["eventReason"] == "TER_RENUNCIA"]
    temprana = (ren["endDate_o"] - ren["inicio"]) < 365.25
    tasa_temp = temprana.sum() / emp_nuevos.sum()                 # renuncias / meses-persona
    tasa_ant = (~temprana).sum() / (emp_c.sum() - emp_nuevos.sum())
    razon = tasa_temp / tasa_ant
    inf.valor("EMP: tasa renuncia ≤12m ÷ >12m", "≈3,3 (2,5–4,0)", num(razon, 2), 2.5 <= razon <= 4.0)

    # Obreros
    t_obr = ter_v[ter_v["clase"] == "OBR"]
    obr_prom = serie.mean() - emp_c.mean()
    rot_obr = (t_obr["eventReason"] != "TER_FIN_OBRA").sum() / obr_prom / (MESES / 12)
    inf.valor("OBR: rotación anual sin fin de obra", "≈30 % (25–35 %)", pct(rot_obr), 0.25 <= rot_obr <= 0.35)
    fo = (t_obr["eventReason"] == "TER_FIN_OBRA").sum()
    inf.valor("OBR: términos por fin de obra al mes", "≈476 (aviso 300–600)", num(fo / MESES),
              300 <= fo / MESES <= 600, solo_aviso=True)
    trf = ((job["eventReason"] == "TRF_OBRA") & (job["employeeClass"] == "OBR") & en_ventana(job["startDate_o"])).sum()
    frac = trf / (trf + fo)
    meta = C.MOVIMIENTOS.obr_fraccion_traslado
    inf.valor("OBR: traslados ÷ sobrantes", f"{pct(meta)} ±3 pp", pct(frac), abs(frac - meta) <= 0.03)
    rehire = ((job["eventReason"] == "REHIRE_OBRA") & en_ventana(job["startDate_o"])).sum()
    inf.valor("OBR: REHIRE ÷ fin de obra", "≈35 % (25–40 %)", pct(rehire / fo), 0.25 <= rehire / fo <= 0.40)

    # Balance de flujo (exacto): stock final − stock inicial = ingresos − términos
    for cl in ("OBR", "EMP"):
        s_ini = (stock(d0 - 1) & (a_clase == cl)).sum()
        s_fin = (stock(d1) & (a_clase == cl)).sum()
        ingresos = (en_ventana(emp["startDate_o"]) & (emp["clase"] == cl)).sum()
        sal = ((ter["endDate_o"] >= d0 - 1) & (ter["endDate_o"] <= d1 - 1) & (ter["clase"] == cl)).sum()
        inf.regla(f"Balance {cl}: Δ dotación = ingresos − términos",
                  int(abs((s_fin - s_ini) - (ingresos - sal))))

    # Personas distintas: identidad exacta A + B + C (Ejercicio 1 de S3)
    toca = emp[(emp["startDate_o"] <= d1) & (emp["endDate_o"] >= d0)]
    distintas = set(toca["personIdExternal"])
    A = set(emp.loc[(emp["startDate_o"] <= d0) & (emp["endDate_o"] >= d0), "personIdExternal"])
    B = set(emp.loc[(emp["originalStartDate_o"] > d0) & (emp["originalStartDate_o"] <= d1), "personIdExternal"])
    C_ = set(emp.loc[(emp["startDate_o"] > d0) & (emp["startDate_o"] <= d1) & (emp["originalStartDate_o"] < d0),
                     "personIdExternal"]) - A
    cuadra = len(A & B) == 0 and len(B & C_) == 0 and distintas == (A | B | C_)
    inf.regla(f"Personas: distintas = A + B + C ({num(len(A))} + {num(len(B))} + {num(len(C_))})",
              0 if cuadra else abs(len(distintas) - len(A | B | C_)) or 1)
    inf.valor("Personas distintas en la ventana", "≈26.000 (aviso 20–33k)", num(len(distintas)),
              20_000 <= len(distintas) <= 33_000, solo_aviso=True)

    # Brecha de género al cierre de la ventana (D-016; tolerancia máx(2 pp; z × error estándar))
    vig_pay = pay[(pay["startDate_o"] <= d1) & (pay["endDate_o"] >= d1)]
    vig_job = job[(job["startDate_o"] <= d1) & (job["endDate_o"] >= d1) & (job["emplStatus"] == "A")]
    genero = t["PerPersonal"].set_index("personIdExternal")["gender"]
    x = vig_job[["userId", "jobCode"]].merge(vig_pay[["userId", "paycompvalue"]], on="userId")
    x["pais"] = x["userId"].map(pais)
    x["genero"] = x["userId"].map(emp.set_index("userId")["personIdExternal"]).map(genero)
    # Se normaliza por el promedio de los hombres del mismo cargo y país (separa CLP de PEN)
    x["rel"] = x["paycompvalue"] / x.groupby(["jobCode", "pais"])["paycompvalue"].transform(
        lambda s: s[x.loc[s.index, "genero"] == "M"].mean())
    z = C.PATRONES.tolerancia_brecha_z
    for c in C.CARGOS:
        f = x[(x["jobCode"] == c.codigo) & (x["genero"] == "F")]["rel"]
        m = x[(x["jobCode"] == c.codigo) & (x["genero"] == "M")]["rel"]
        if len(f) < 2 or len(m) < 2:
            inf.valor(f"Brecha {c.codigo}", "—", f"n mujeres = {len(f)}", False, solo_aviso=True)
            continue
        brecha = f.mean() - 1
        meta = C.PATRONES.brecha_genero.get(c.codigo, 0.0)
        ee = float(np.sqrt(f.var() / len(f) + m.var() / len(m)))
        tol = max(C.PATRONES.tolerancia_brecha_min, z * ee)
        inf.valor(f"Brecha {c.codigo} (n M/H {len(f)}/{len(m)})", f"{pct(meta)} ±{tol * 100:.1f} pp".replace(".", ","),
                  pct(brecha), abs(brecha - meta) <= tol)


def main() -> int:
    if not DATOS.exists():
        print("No hay datos: primero corre python generator/generar.py")
        return 1
    nombres = ["EmpJob", "EmpEmployment", "EmpEmploymentTermination", "EmpPayCompRecurring", "PerPerson",
               "PerPersonal", "PerNationalId", "FOLocation", "FOEventReason", "FOCompany", "FOJobCode",
               "FODepartment", "FODivision", "FOBusinessUnit"]
    t = {n: leer(n) for n in nombres}
    print(f"PA Lab · validación de datos · ventana {D0} a {D1}")
    inf = Informe()
    reglas(t, inf)
    inf.imprimir("A. Reglas exactas del diccionario (§8)")
    valores(t, inf)
    inf.imprimir("B. Valores esperados (diseño §3) y balances exactos")
    e, a = inf.errores(), inf.avisos()
    print()
    print(f"{'VALIDACIÓN OK ✔' if e == 0 else f'VALIDACIÓN CON {e} ERROR(ES) ✘'} · {a} aviso(s)")
    return 0 if e == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
