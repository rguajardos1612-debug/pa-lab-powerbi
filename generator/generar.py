"""
generar.py — Generador de datos ficticios de Grupo Cordillera Sur S.A. (Fase 1, S3).

Uso (desde la raíz del repo, con .venv activado):
    python generator/generar.py

Sigue el algoritmo de docs/diseno_generador.md §2:
    0 validar → 1 catálogos → 2 obras → 3 dotación objetivo → 4 población semilla
    → 5 simulación mes a mes → 6 eventos a tablas → 7 personas → 9 escritura
(el paso 8, validación de datos, está en generator/validar.py).

Todos los números que definen a la empresa están en config.py. Con la misma semilla
y el mismo código salen exactamente los mismos datos (D-003).
Todos los datos son inventados. Ninguno viene de una empresa real.
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "data"
FIN = C.IDS.fecha_abierta
UN_DIA = timedelta(days=1)
DIAS_POR_MES = 30.4375

# ─────────────────────────────────────────────────────────────────────────────
# Tablas de apoyo derivadas de config (no agregan números nuevos)
# ─────────────────────────────────────────────────────────────────────────────
CARGO = {c.codigo: c for c in C.CARGOS}
CARGOS_DE_CLASE = {cl: [c.codigo for c in C.CARGOS if c.clase == cl]
                   for cl in C.DOTACION.participacion_clase}
PAISES = list(C.DOTACION.participacion_pais)
COMPANIA_DE = {v["country"]: k for k, v in C.COMPANIAS.items()}
MONEDA_DE = {v["country"]: v["currency"] for v in C.COMPANIAS.values()}
SUFIJO_PAIS = {p: COMPANIA_DE[p].split("_")[1] for p in PAISES}          # CHL → CL
OFICINA_DE = {v["country"]: k for k, v in C.OFICINAS.items()}
MOTIVO = {r[0]: r for r in C.EVENT_REASONS}                              # código → fila
PESO_EN_OBRA = sum(CARGO[c].peso for c in C.CARGOS_EN_OBRA)
FRACCION_AJUSTE_EN_OBRA = ((C.DOTACION.empleados_en_obra - PESO_EN_OBRA)
                           / CARGO[C.CARGO_AJUSTE_OBRA].peso)


# ─────────────────────────────────────────────────────────────────────────────
# Fechas: los meses se numeran respecto de Periodo.primer_mes (0 = 2023-11)
# El calentamiento va de −24 a −1; la ventana de análisis, de 0 a 35.
# ─────────────────────────────────────────────────────────────────────────────
def mes(i: int) -> date:
    """Primer día del mes i."""
    base = C.PERIODO.primer_mes
    k = base.year * 12 + base.month - 1 + i
    return date(k // 12, k % 12 + 1, 1)


def fin_mes(i: int) -> date:
    """Último día del mes i."""
    return mes(i + 1) - UN_DIA


def anio_banda(d: date) -> int:
    """Año de la banda salarial vigente en d (la banda cambia en el mes del reajuste)."""
    return d.year if d.month >= C.REMUNERACION.reajuste_mes else d.year - 1


I_INICIO = -C.PERIODO.meses_calentamiento
I_FIN = C.PERIODO.meses - 1
ANIO_REFERENCIA = anio_banda(fin_mes(I_FIN))   # sueldo_medio de config vale en este año (D-017)


def medio_cargo(cargo: str, pais: str, d: date) -> float:
    """Punto medio de la banda del cargo vigente en d: se descuentan los reajustes (D-017)."""
    valor = float(CARGO[cargo].sueldo_medio[pais])
    for _ in range(anio_banda(d) + 1, ANIO_REFERENCIA + 1):
        valor /= 1 + C.REMUNERACION.reajuste_pct[pais]
    return valor


def brecha(cargo: str, genero: str) -> float:
    """Factor de la brecha plantada: solo mujeres y solo en algunos cargos (D-016)."""
    return 1 + C.PATRONES.brecha_genero.get(cargo, 0.0) if genero == "F" else 1.0


def division_fija(cargo: str) -> dict[str, float] | None:
    return C.DIVISION_CARGO.get(cargo)


def reparto_entero(total: int, pesos: list[float]) -> list[int]:
    """Reparte un total entero según pesos (método del resto mayor): la suma es exacta."""
    s = sum(pesos)
    if total <= 0 or s <= 0:
        return [0] * len(pesos)
    exactos = [total * w / s for w in pesos]
    enteros = [math.floor(x) for x in exactos]
    faltan = total - sum(enteros)
    orden = sorted(range(len(pesos)), key=lambda k: exactos[k] - enteros[k], reverse=True)
    for k in orden[:faltan]:
        enteros[k] += 1
    return enteros


# ─────────────────────────────────────────────────────────────────────────────
# Objetos de la simulación
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Obra:
    codigo: str
    pais: str
    bu: str
    region: str
    m_ini: int          # mes de inicio (índice)
    m_fin: int          # último mes con actividad (índice, incluido)
    tamano: float       # tamaño relativo del peak

    def activa(self, i: int) -> bool:
        return self.m_ini <= i <= self.m_fin

    def forma(self, i: int) -> float:
        """Trapecio: sube, se mantiene en su peak y baja. 0 si la obra no está activa."""
        if not self.activa(i):
            return 0.0
        largo = self.m_fin - self.m_ini + 1
        t = (i - self.m_ini + 0.5) / largo
        sube, baja = C.OBRAS.fraccion_subida, C.OBRAS.fraccion_bajada
        if t < sube:
            nivel = t / sube
        elif t > 1 - baja:
            nivel = (1 - t) / baja
        else:
            nivel = 1.0
        return self.tamano * nivel


@dataclass
class Persona:
    personIdExternal: str
    pais: str
    genero: str
    nacimiento: date
    inicio_original: date


@dataclass
class Empleo:
    userId: str
    persona: Persona
    pais: str
    clase: str
    inicio: date
    cargo: str
    location: str
    division: str
    sueldo: float
    ultimo_evento_job: date


# ─────────────────────────────────────────────────────────────────────────────
# Simulación
# ─────────────────────────────────────────────────────────────────────────────
class Simulacion:
    def __init__(self) -> None:
        self.rng = np.random.default_rng(C.SEED)
        self.obras: dict[str, list[Obra]] = {p: [] for p in PAISES}
        self.obra_por_codigo: dict[str, Obra] = {}
        self.activos: dict[str, Empleo] = {}
        self.personas: list[Persona] = []
        self.empleos: dict[str, dict] = {}              # userId → fila de EmpEmployment
        self.terminos: list[dict] = []                   # filas de EmpEmploymentTermination
        self.ev_job: list[dict] = []                     # eventos → EmpJob
        self.ev_pago: list[dict] = []                    # eventos → EmpPayCompRecurring
        self.pool_rehire: dict[str, list[tuple[int, Persona, str]]] = {p: [] for p in PAISES}
        self.factor: dict[str, dict[int, float]] = {p: {} for p in PAISES}
        self._objetivos: dict[int, dict] = {}
        self._n_persona = 0
        self._n_empleo = 0
        self._orden = 0

    # ── utilidades ──────────────────────────────────────────────────────────
    def azar(self) -> float:
        return float(self.rng.random())

    def elegir(self, opciones: list, pesos: list[float]):
        p = np.asarray(pesos, dtype=float)
        return opciones[int(self.rng.choice(len(opciones), p=p / p.sum()))]

    def dia_al_azar(self, i: int) -> date:
        dias = (fin_mes(i) - mes(i)).days + 1
        return mes(i) + timedelta(days=int(self.rng.integers(dias)))

    def es_obra(self, location: str) -> bool:
        return location in self.obra_por_codigo

    def bu_de(self, location: str) -> str:
        if self.es_obra(location):
            return self.obra_por_codigo[location].bu
        return C.OFICINAS[location]["businessUnit"]

    # ── 2. Obras ────────────────────────────────────────────────────────────
    def crear_obras(self) -> None:
        o = C.OBRAS
        dur_media = (o.duracion_min_meses + o.duracion_max_meses) / 2
        for pais in PAISES:
            # Ley de Little: si nacen λ obras al mes y duran D meses, hay λ·D activas
            lam = o.activas_promedio[pais] / dur_media
            creadas = []
            for i in range(I_INICIO - o.duracion_max_meses, I_FIN + 1):
                for _ in range(int(self.rng.poisson(lam))):
                    largo = int(self.rng.integers(o.duracion_min_meses, o.duracion_max_meses + 1))
                    if i + largo - 1 < I_INICIO:
                        continue                      # terminó antes del calentamiento
                    bu = self.elegir(list(o.mix_unidad), list(o.mix_unidad.values()))
                    region = C.REGIONES_OBRA[pais][int(self.rng.integers(len(C.REGIONES_OBRA[pais])))]
                    tamano = float(self.rng.lognormal(0.0, o.dispersion_tamano))
                    creadas.append((i, largo, bu, region, tamano))
            creadas.sort(key=lambda x: x[0])
            for n, (i, largo, bu, region, tamano) in enumerate(creadas, start=1):
                obra = Obra(f"OB_{SUFIJO_PAIS[pais]}_{n:03d}", pais, bu, region, i, i + largo - 1, tamano)
                self.obras[pais].append(obra)
                self.obra_por_codigo[obra.codigo] = obra

    def obras_activas(self, pais: str, i: int) -> list[Obra]:
        return [o for o in self.obras[pais] if o.activa(i)]

    # ── 3. Dotación objetivo ────────────────────────────────────────────────
    def objetivos(self, i: int) -> dict:
        """Objetivo de cierre del mes i por país: empleados, obreros y obreros por obra."""
        if i in self._objetivos:
            return self._objetivos[i]
        d = C.DOTACION
        total = d.promedio_cierre_mes * (1 + d.oscilacion * math.sin(2 * math.pi * i / d.ciclo_meses))
        resultado = {}
        for pais, part in d.participacion_pais.items():
            emp = round(d.promedio_cierre_mes * d.participacion_clase["EMP"] * part)   # estable (D-012)
            obr = round(total * part) - emp                                            # absorbe el ciclo
            activas = self.obras_activas(pais, i)
            formas = [ob.forma(i) for ob in activas]
            # D-014: un factor común por mes reescala los trapecios para cumplir el objetivo
            self.factor[pais][i] = obr / sum(formas) if formas else float("nan")
            por_obra = dict(zip([ob.codigo for ob in activas], reparto_entero(obr, formas)))
            resultado[pais] = {"EMP": emp, "OBR": obr, "por_obra": por_obra}
        self._objetivos[i] = resultado
        return resultado

    def objetivo_cargo(self, pais: str, clase: str, i: int) -> dict[str, float]:
        total = self.objetivos(i)[pais][clase]
        return {c: total * CARGO[c].peso for c in CARGOS_DE_CLASE[clase]}

    # ── registro de eventos (Principio 3: solo eventos, las fechas de fin salen al final) ──
    def evento_job(self, e: Empleo, fecha: date, motivo: str) -> None:
        # D-019: como máximo un evento de EmpJob por empleo y día (seqNumber = 1)
        if fecha == e.ultimo_evento_job and motivo not in ("HIRE_NEW", "REHIRE_OBRA"):
            raise RuntimeError(f"{e.userId}: dos eventos de EmpJob el {fecha}")
        self._orden += 1
        self.ev_job.append({
            "_orden": self._orden, "userId": e.userId, "startDate": fecha,
            "event": MOTIVO[motivo][2], "eventReason": motivo, "emplStatus": MOTIVO[motivo][3],
            "company": COMPANIA_DE[e.pais], "businessUnit": self.bu_de(e.location),
            "division": e.division, "department": f"DEP_{e.division[4:]}_{SUFIJO_PAIS[e.pais]}",
            "location": e.location, "jobCode": e.cargo, "payGrade": CARGO[e.cargo].grado,
            "employeeClass": e.clase, "contractType": C.CONTRATO_CLASE[e.clase],
            "standardHours": C.HORAS_SEMANALES[e.pais], "fte": 1.0,
        })
        e.ultimo_evento_job = fecha

    def evento_pago(self, e: Empleo, fecha: date, motivo: str) -> None:
        self._orden += 1
        self.ev_pago.append({"_orden": self._orden, "userId": e.userId, "startDate": fecha,
                             "eventReason": motivo, "valor": e.sueldo, "pais": e.pais})

    # ── personas y empleos ──────────────────────────────────────────────────
    def nueva_persona(self, pais: str, clase: str, fecha_ingreso: date) -> Persona:
        dm = C.DEMOGRAFIA
        self._n_persona += 1
        genero = "F" if self.azar() < dm.proporcion_mujeres[clase] else "M"
        edad = float(np.clip(self.rng.normal(dm.edad_ingreso_media[clase], dm.edad_ingreso_desv),
                             dm.edad_ingreso_min, dm.edad_ingreso_max))
        nacimiento = fecha_ingreso - timedelta(days=int(edad * 365.25))
        p = Persona(f"{C.IDS.prefijo_persona}{self._n_persona:0{C.IDS.digitos_persona}d}",
                    pais, genero, nacimiento, fecha_ingreso)
        self.personas.append(p)
        return p

    def division_para(self, cargo: str, clase: str) -> str:
        reparto = division_fija(cargo) or C.DIVISION_CARGO[clase]
        return self.elegir(list(reparto), list(reparto.values()))

    def sueldo_ingreso(self, cargo: str, pais: str, fecha: date, genero: str) -> float:
        r = C.REMUNERACION
        z = float(np.clip(self.rng.normal(1.0, r.dispersion_ingreso), r.banda_min, r.banda_max))
        return medio_cargo(cargo, pais, fecha) * z * brecha(cargo, genero)

    def contratar(self, pais: str, clase: str, cargo: str, location: str, fecha: date,
                  persona: Persona | None = None, fecha_sueldo: date | None = None) -> Empleo:
        recontratacion = persona is not None
        if persona is None:
            persona = self.nueva_persona(pais, clase, fecha)
        self._n_empleo += 1
        e = Empleo(
            userId=f"{C.IDS.prefijo_empleo}{self._n_empleo:0{C.IDS.digitos_empleo}d}",
            persona=persona, pais=pais, clase=clase, inicio=fecha, cargo=cargo, location=location,
            division=self.division_para(cargo, clase),
            sueldo=self.sueldo_ingreso(cargo, pais, fecha_sueldo or fecha, persona.genero),
            ultimo_evento_job=fecha,
        )
        motivo = "REHIRE_OBRA" if recontratacion else "HIRE_NEW"
        self.evento_job(e, fecha, motivo)
        self.evento_pago(e, fecha, motivo)
        self.empleos[e.userId] = {
            "userId": e.userId, "personIdExternal": persona.personIdExternal, "startDate": fecha,
            "endDate": FIN, "originalStartDate": persona.inicio_original, "isPrimary": True,
        }
        self.activos[e.userId] = e
        return e

    def terminar(self, e: Empleo, ultimo_dia: date, motivo: str) -> None:
        """D-008: el último día queda en EmpEmployment.endDate; TERMINATION parte al día siguiente."""
        self.evento_job(e, ultimo_dia + UN_DIA, motivo)
        self.empleos[e.userId]["endDate"] = ultimo_dia
        ok = self.azar() < C.MOVIMIENTOS.ok_recontratar[motivo]
        self.terminos.append({"userId": e.userId, "endDate": ultimo_dia,
                              "eventReason": motivo, "okToRehire": ok})
        del self.activos[e.userId]

    # ── ubicación de un empleado ────────────────────────────────────────────
    def obra_al_azar(self, pais: str, i: int, excluir: str | None = None) -> str | None:
        activas = [o for o in self.obras_activas(pais, i) if o.codigo != excluir]
        if not activas:
            return None
        return self.elegir([o.codigo for o in activas], [o.forma(i) for o in activas])

    def ubicacion_empleado(self, pais: str, cargo: str, i: int, ajuste_en_obra: int,
                           ajuste_total: int) -> str:
        """Cargos de obra → una obra activa; cargo de ajuste → obra si falta para su fracción;
        el resto → oficina."""
        oficina = OFICINA_DE[pais]
        if cargo in C.CARGOS_EN_OBRA:
            return self.obra_al_azar(pais, i) or oficina
        if cargo == C.CARGO_AJUSTE_OBRA and ajuste_en_obra < FRACCION_AJUSTE_EN_OBRA * (ajuste_total + 1):
            return self.obra_al_azar(pais, i) or oficina
        return oficina

    # ── 4. Población semilla ────────────────────────────────────────────────
    def pmf_antiguedad(self, clase: str, max_meses: int) -> np.ndarray:
        """Distribución de antigüedad de flujo estable: P(a) ∝ supervivencia S(a)."""
        m = C.MOVIMIENTOS
        s, sup = 1.0, []
        for a in range(max_meses + 1):
            sup.append(s)
            if clase == "EMP":
                ren = m.emp_renuncia_hasta_12m if a < 12 else m.emp_renuncia_desde_13m
                h = ren + m.emp_nec_empresa + m.emp_disciplinario + m.emp_mutuo_acuerdo
            else:
                h = m.obr_renuncia + m.obr_nec_empresa + m.obr_disciplinario
            s *= 1 - h
        p = np.asarray(sup)
        return p / p.sum()

    def antiguedad_dias(self, clase: str, max_dias: int) -> int:
        max_meses = max(0, int(max_dias // DIAS_POR_MES))
        pmf = self.pmf_antiguedad(clase, max_meses)
        a = int(self.rng.choice(len(pmf), p=pmf))
        return min(max_dias, int(a * DIAS_POR_MES + self.rng.integers(int(DIAS_POR_MES))))

    def crear_semilla(self) -> None:
        i = I_INICIO
        d0 = mes(i)
        tope = int(C.PERIODO.antiguedad_semilla_max_anios * 365.25)
        obj = self.objetivos(i)
        for pais in PAISES:
            # Empleados: antigüedad de flujo estable, con tope de 15 años
            cargos = CARGOS_DE_CLASE["EMP"]
            cantidades = reparto_entero(obj[pais]["EMP"], [CARGO[c].peso for c in cargos])
            for cargo, n in zip(cargos, cantidades):
                en_obra = 0
                for k in range(n):
                    loc = self.ubicacion_empleado(pais, cargo, i, en_obra, k)
                    en_obra += self.es_obra(loc)
                    inicio = d0 - timedelta(days=self.antiguedad_dias("EMP", tope))
                    inicio_obra = mes(self.obra_por_codigo[loc].m_ini) if self.es_obra(loc) else None
                    if inicio_obra and inicio < inicio_obra:
                        # Regla 8: antes de que la obra existiera, estaba en la oficina
                        e = self.contratar(pais, "EMP", cargo, OFICINA_DE[pais], inicio, fecha_sueldo=d0)
                        e.location = loc
                        self.evento_job(e, inicio_obra, "TRF_OBRA")
                    else:
                        self.contratar(pais, "EMP", cargo, loc, inicio, fecha_sueldo=d0)
            # Obreros: antigüedad acotada por el inicio de su obra (regla 8)
            cargos = CARGOS_DE_CLASE["OBR"]
            pesos = [CARGO[c].peso for c in cargos]
            for codigo, n in obj[pais]["por_obra"].items():
                inicio_obra = mes(self.obra_por_codigo[codigo].m_ini)
                for _ in range(n):
                    cargo = self.elegir(cargos, pesos)
                    dias = self.antiguedad_dias("OBR", min(tope, (d0 - inicio_obra).days))
                    self.contratar(pais, "OBR", cargo, codigo, d0 - timedelta(days=dias), fecha_sueldo=d0)

    # ── 5. Simulación de un mes ─────────────────────────────────────────────
    def paso_fin_de_obra(self, i: int) -> None:
        """5a (parte 1). Obreros sobrantes: traslado (D-013) o TER_FIN_OBRA. Empleados de obras
        cerradas: TRF_OBRA u oficina (D-012). Fechas: término el último día del mes anterior,
        traslado el primer día del mes."""
        d0 = mes(i)
        obj = self.objetivos(i)
        for pais in PAISES:
            obreros_por_obra: dict[str, list[Empleo]] = {}
            empleados_en_obras_cerradas: list[Empleo] = []
            for e in self.activos.values():
                if e.pais != pais or not self.es_obra(e.location):
                    continue
                if e.clase == "OBR":
                    obreros_por_obra.setdefault(e.location, []).append(e)
                elif not self.obra_por_codigo[e.location].activa(i):
                    empleados_en_obras_cerradas.append(e)
            meta = obj[pais]["por_obra"]
            sobrantes: list[Empleo] = []
            for codigo, lista in obreros_por_obra.items():
                exceso = len(lista) - meta.get(codigo, 0)
                if exceso > 0:
                    idx = self.rng.choice(len(lista), size=exceso, replace=False)
                    sobrantes.extend(lista[int(k)] for k in idx)
            deficit = {c: n - len(obreros_por_obra.get(c, [])) for c, n in meta.items()}
            deficit = {c: d for c, d in deficit.items() if d > 0}
            for e in sobrantes:
                if deficit and self.azar() < C.MOVIMIENTOS.obr_fraccion_traslado:
                    destino = self.elegir(list(deficit), list(deficit.values()))
                    e.location = destino
                    self.evento_job(e, d0, "TRF_OBRA")
                    deficit[destino] -= 1
                    if deficit[destino] == 0:
                        del deficit[destino]
                else:
                    self.terminar(e, d0 - UN_DIA, "TER_FIN_OBRA")
                    if self.azar() < C.MOVIMIENTOS.obr_prob_recontratacion:
                        pausa = int(self.rng.integers(C.MOVIMIENTOS.obr_pausa_min_meses,
                                                      C.MOVIMIENTOS.obr_pausa_max_meses + 1))
                        self.pool_rehire[pais].append((i + pausa, e.persona, e.cargo))
            for e in empleados_en_obras_cerradas:
                destino = None
                if e.cargo in C.CARGOS_EN_OBRA:
                    destino = self.obra_al_azar(pais, i, excluir=e.location)
                if destino:
                    e.location = destino
                    self.evento_job(e, d0, "TRF_OBRA")
                else:
                    e.location = OFICINA_DE[pais]
                    self.evento_job(e, d0, "TRF_OFICINA")

    def paso_remuneracion(self, i: int) -> None:
        """5c. Reajuste (todos) y mérito (solo empleados) el primer día del mes."""
        d0 = mes(i)
        r = C.REMUNERACION
        for e in self.activos.values():
            if e.inicio >= d0:
                continue
            if d0.month == r.reajuste_mes:
                e.sueldo *= 1 + r.reajuste_pct[e.pais]
                self.evento_pago(e, d0, "PAY_REAJ")
            if d0.month == r.merito_mes and e.clase == "EMP" and self.azar() < r.merito_fraccion_elegible:
                e.sueldo *= 1 + r.merito_pct_medio
                self.evento_pago(e, d0, "PAY_MERIT")

    def paso_terminos(self, i: int) -> None:
        """5a (parte 2). Términos por probabilidad, en un día al azar del mes."""
        m = C.MOVIMIENTOS
        d0 = mes(i)
        for e in list(self.activos.values()):
            if e.inicio >= d0:
                continue
            if e.clase == "OBR":
                probs = {"TER_RENUNCIA": m.obr_renuncia, "TER_NEC_EMP": m.obr_nec_empresa,
                         "TER_DISCIPL": m.obr_disciplinario}
            else:
                meses_antig = (d0 - e.inicio).days / DIAS_POR_MES
                ren = m.emp_renuncia_hasta_12m if meses_antig < 12 else m.emp_renuncia_desde_13m
                probs = {"TER_RENUNCIA": ren, "TER_NEC_EMP": m.emp_nec_empresa,
                         "TER_DISCIPL": m.emp_disciplinario, "TER_MUTUO": m.emp_mutuo_acuerdo}
            u, acumulado = self.azar(), 0.0
            for motivo, p in probs.items():
                acumulado += p
                if u < acumulado:
                    ultimo = max(self.dia_al_azar(i), e.ultimo_evento_job)
                    self.terminar(e, ultimo, motivo)
                    break

    def paso_movimientos(self, i: int) -> None:
        """5b. Promociones con vacante (D-015, D-016) y cambios de área, el primer día del mes."""
        d0 = mes(i)
        m = C.MOVIMIENTOS
        for pais in PAISES:
            libres = [e for e in self.activos.values()
                      if e.pais == pais and e.ultimo_evento_job != d0 and e.inicio < d0]
            conteo: dict[str, int] = {}
            for e in self.activos.values():
                if e.pais == pais:
                    conteo[e.cargo] = conteo.get(e.cargo, 0) + 1
            # Destinos de arriba hacia abajo: una vacante en GER abre otra en SUB el mismo mes.
            # dict.fromkeys (no set): el orden de un set de textos cambia en cada ejecución y,
            # con empates de sueldo (CAP y ANA en Perú), rompería la reproducibilidad (D-003).
            destinos = sorted(dict.fromkeys(C.ESCALERA.values()), key=lambda c: -CARGO[c].sueldo_medio[pais])
            promovidos: set[str] = set()
            for destino in destinos:
                clase = CARGO[destino].clase
                vacantes = int(self.objetivo_cargo(pais, clase, i)[destino]) - conteo.get(destino, 0)
                if vacantes <= 0:
                    continue
                prob = m.obr_promocion if clase == "OBR" else m.emp_promocion
                origenes = [o for o, d in C.ESCALERA.items() if d == destino]
                candidatos = [e for e in libres if e.cargo in origenes and e.userId not in promovidos
                              and self.azar() < prob]
                self.rng.shuffle(candidatos)
                for e in candidatos[:vacantes]:
                    conteo[e.cargo] -= 1                     # deja una vacante en su cargo
                    self.promover(e, destino, i)
                    conteo[destino] = conteo.get(destino, 0) + 1
                    promovidos.add(e.userId)
            for e in libres:
                if (e.userId in promovidos or e.clase != "EMP" or division_fija(e.cargo)
                        or self.azar() >= m.emp_transferencia_area):
                    continue
                reparto = {d: w for d, w in C.DIVISION_CARGO["EMP"].items() if d != e.division}
                e.division = self.elegir(list(reparto), list(reparto.values()))
                self.evento_job(e, d0, "TRF_AREA")

    def promover(self, e: Empleo, destino: str, i: int) -> None:
        d0 = mes(i)
        g = e.persona.genero
        # D-016: se conserva la posición en la banda (z); la brecha es la del cargo de destino
        z = e.sueldo / (medio_cargo(e.cargo, e.pais, d0) * brecha(e.cargo, g))
        nuevo = max(e.sueldo * (1 + C.REMUNERACION.promocion_pct),
                    medio_cargo(destino, e.pais, d0) * z * brecha(destino, g))
        e.cargo, e.sueldo = destino, nuevo
        if division_fija(destino):
            e.division = self.division_para(destino, e.clase)
        if e.clase == "EMP":
            if destino in C.CARGOS_EN_OBRA:
                if not self.es_obra(e.location):
                    e.location = self.obra_al_azar(e.pais, i) or e.location
            elif self.es_obra(e.location):
                e.location = OFICINA_DE[e.pais]
        self.evento_job(e, d0, "PRO_PROM")
        self.evento_pago(e, d0, "PRO_PROM")

    def paso_contrataciones(self, i: int) -> None:
        """5d. Cubrir la brecha con el objetivo: primero REHIRE, después HIRE."""
        obj = self.objetivos(i)
        for pais in PAISES:
            conteo = {c: 0 for c in CARGO}
            obreros_obra: dict[str, int] = {}
            ajuste_en_obra = 0
            for e in self.activos.values():
                if e.pais != pais:
                    continue
                conteo[e.cargo] += 1
                if e.clase == "OBR":
                    obreros_obra[e.location] = obreros_obra.get(e.location, 0) + 1
                elif e.cargo == C.CARGO_AJUSTE_OBRA and self.es_obra(e.location):
                    ajuste_en_obra += 1

            def cargo_por_deficit(clase: str) -> str:
                meta = self.objetivo_cargo(pais, clase, i)
                cargos = CARGOS_DE_CLASE[clase]
                faltan = [max(0.0, meta[c] - conteo[c]) for c in cargos]
                if sum(faltan) == 0:
                    faltan = [CARGO[c].peso for c in cargos]
                return self.elegir(cargos, faltan)

            # Empleados
            n_emp = sum(conteo[c] for c in CARGOS_DE_CLASE["EMP"])
            for _ in range(obj[pais]["EMP"] - n_emp):
                cargo = cargo_por_deficit("EMP")
                loc = self.ubicacion_empleado(pais, cargo, i, ajuste_en_obra, conteo[C.CARGO_AJUSTE_OBRA])
                if cargo == C.CARGO_AJUSTE_OBRA and self.es_obra(loc):
                    ajuste_en_obra += 1
                self.contratar(pais, "EMP", cargo, loc, self.dia_al_azar(i))
                conteo[cargo] += 1

            # Obreros: por obra; primero recontrataciones con la pausa cumplida
            disponibles = sorted((x for x in self.pool_rehire[pais] if x[0] <= i), key=lambda x: x[0])
            esperando = [x for x in self.pool_rehire[pais] if x[0] > i]
            for codigo, meta in obj[pais]["por_obra"].items():
                for _ in range(meta - obreros_obra.get(codigo, 0)):
                    fecha = self.dia_al_azar(i)
                    if disponibles:
                        _, persona, cargo = disponibles.pop(0)
                        self.contratar(pais, "OBR", cargo, codigo, fecha, persona=persona)
                    else:
                        cargo = cargo_por_deficit("OBR")
                        self.contratar(pais, "OBR", cargo, codigo, fecha)
                    conteo[cargo] += 1
            self.pool_rehire[pais] = disponibles + esperando

    def simular(self) -> None:
        for i in range(I_INICIO + 1, I_FIN + 1):
            self.paso_fin_de_obra(i)
            self.paso_remuneracion(i)
            self.paso_terminos(i)
            self.paso_movimientos(i)
            self.paso_contrataciones(i)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Eventos → tablas con vigencia
# ─────────────────────────────────────────────────────────────────────────────
def cerrar_vigencias(df: pd.DataFrame, fin_por_empleo: dict[str, date] | None = None) -> pd.DataFrame:
    """endDate = día anterior al startDate de la fila siguiente del mismo userId.
    La última fila termina en 9999-12-31 (o en EmpEmployment.endDate si se indica)."""
    df = df.sort_values(["userId", "startDate", "_orden"], kind="stable").reset_index(drop=True)
    usuarios, inicios = df["userId"].tolist(), df["startDate"].tolist()
    fines = []
    for k, u in enumerate(usuarios):
        if k + 1 < len(usuarios) and usuarios[k + 1] == u:
            fines.append(inicios[k + 1] - UN_DIA)
        else:
            fines.append(fin_por_empleo.get(u, FIN) if fin_por_empleo else FIN)
    df.insert(df.columns.get_loc("startDate") + 1, "endDate", fines)
    return df


def redondear(valor: float, pais: str) -> float:
    """CLP sin decimales; PEN con 2 decimales."""
    return float(round(valor)) if MONEDA_DE[pais] == "CLP" else round(valor, 2)


def tablas_empleo(sim: Simulacion) -> dict[str, pd.DataFrame]:
    job = cerrar_vigencias(pd.DataFrame(sim.ev_job))
    job.insert(job.columns.get_loc("endDate") + 1, "seqNumber", 1)
    job = job.drop(columns="_orden")

    empleo = pd.DataFrame(list(sim.empleos.values()))
    fin_empleo = {u: f for u, f in zip(empleo["userId"], empleo["endDate"]) if f != FIN}

    pago = pd.DataFrame(sim.ev_pago).sort_values("_orden")
    # Si hay dos cambios de sueldo el mismo día (p. ej., reajuste y promoción), queda el
    # último: su monto ya incluye el anterior y su motivo es el más específico.
    pago = pago.drop_duplicates(["userId", "startDate"], keep="last")
    pago = cerrar_vigencias(pago, fin_empleo).drop(columns="_orden")
    pago["paycompvalue"] = [redondear(v, p) for v, p in zip(pago["valor"], pago["pais"])]
    pago["currencyCode"] = pago["pais"].map(MONEDA_DE)
    pago["payComponent"] = "SUELDO_BASE"
    pago["frequency"] = "MON"
    pago = pago[["userId", "startDate", "endDate", "eventReason", "payComponent",
                 "paycompvalue", "currencyCode", "frequency"]]

    termino = pd.DataFrame(sim.terminos)
    return {"EmpEmployment": empleo, "EmpEmploymentTermination": termino,
            "EmpJob": job, "EmpPayCompRecurring": pago}


def tablas_catalogo(sim: Simulacion) -> dict[str, pd.DataFrame]:
    company = pd.DataFrame([{"externalCode": k, **v} for k, v in C.COMPANIAS.items()])
    bu = pd.DataFrame([{"externalCode": k, "name": v} for k, v in C.UNIDADES_NEGOCIO.items()])
    # Las gerencias son transversales a las unidades de negocio (estructura matricial)
    division = pd.DataFrame([{"externalCode": k, "name": v, "businessUnit": None}
                             for k, v in C.GERENCIAS.items()])
    nombre_pais = {c["country"]: c["name"].split()[-2] for c in C.COMPANIAS.values()}
    department = pd.DataFrame([
        {"externalCode": f"DEP_{k[4:]}_{SUFIJO_PAIS[p]}", "name": f"{v} {nombre_pais[p]}", "division": k}
        for k, v in C.GERENCIAS.items() for p in PAISES])
    lugares = [{"externalCode": o.codigo,
                "name": f"{C.UNIDADES_NEGOCIO[o.bu]} {o.region} {o.codigo[-3:]}",
                "country": o.pais, "region": o.region, "cust_tipo": "OBRA",
                "cust_obraInicio": mes(o.m_ini), "cust_obraFin": fin_mes(o.m_fin)}
               for p in PAISES for o in sim.obras[p]]
    lugares += [{"externalCode": k, "name": v["name"], "country": v["country"], "region": v["region"],
                 "cust_tipo": "OFICINA", "cust_obraInicio": None, "cust_obraFin": None}
                for k, v in C.OFICINAS.items()]
    location = pd.DataFrame(lugares)
    jobcode = pd.DataFrame([{"externalCode": c.codigo, "name": c.nombre, "employeeClass": c.clase,
                             "payGrade": c.grado} for c in C.CARGOS])
    # FOPayGrade con vigencia anual (D-017). El medio del grado es el promedio de sus
    # cargos ponderado por peso (un grado agrupa cargos con distinto punto medio).
    filas = []
    anios = range(anio_banda(mes(I_INICIO)), ANIO_REFERENCIA + 1)
    grados = sorted({c.grado for c in C.CARGOS})
    for g in grados:
        cargos = [c for c in C.CARGOS if c.grado == g]
        for p in PAISES:
            for y in anios:
                d = date(y, C.REMUNERACION.reajuste_mes, 1)
                medio = sum(medio_cargo(c.codigo, p, d) * c.peso for c in cargos) / sum(c.peso for c in cargos)
                filas.append({"externalCode": g, "name": f"Grado {g[3:]}", "country": p, "startDate": d,
                              "endDate": date(y + 1, C.REMUNERACION.reajuste_mes, 1) - UN_DIA
                              if y < ANIO_REFERENCIA else FIN,
                              "minimo": redondear(medio * C.REMUNERACION.banda_min, p),
                              "medio": redondear(medio, p),
                              "maximo": redondear(medio * C.REMUNERACION.banda_max, p)})
    paygrade = pd.DataFrame(filas)
    reason = pd.DataFrame(C.EVENT_REASONS, columns=["externalCode", "name", "event", "emplStatus",
                                                    "cust_tipoRotacion"])
    return {"FOCompany": company, "FOBusinessUnit": bu, "FODivision": division,
            "FODepartment": department, "FOLocation": location, "FOJobCode": jobcode,
            "FOPayGrade": paygrade, "FOEventReason": reason}


# ─────────────────────────────────────────────────────────────────────────────
# 7. Personas (PerPerson, PerPersonal, PerNationalId)
# ─────────────────────────────────────────────────────────────────────────────
def digito_verificador(numero: int) -> str:
    """Módulo 11, como un RUT (D-007)."""
    suma, factor = 0, 2
    for d in reversed(str(numero)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - suma % 11
    return {11: "0", 10: "K"}.get(resto, str(resto))


def tablas_persona(sim: Simulacion) -> dict[str, pd.DataFrame]:
    Faker.seed(C.SEED)
    fakers = {p: Faker(C.DEMOGRAFIA.locale_faker[p]) for p in PAISES}
    rng = np.random.default_rng(C.SEED + 1)
    estados = list(C.DEMOGRAFIA.estado_civil)
    pesos = np.asarray(list(C.DEMOGRAFIA.estado_civil.values()))
    ids = C.IDS
    usados: set[int] = set()
    per, personal, doc = [], [], []
    for p in sim.personas:
        f = fakers[p.pais]
        per.append({"personIdExternal": p.personIdExternal, "dateOfBirth": p.nacimiento,
                    "countryOfBirth": p.pais})
        nombre = f.first_name_female() if p.genero == "F" else f.first_name_male()
        personal.append({"personIdExternal": p.personIdExternal, "startDate": p.inicio_original,
                         "endDate": FIN, "firstName": nombre,
                         "lastName": f"{f.last_name()} {f.last_name()}", "gender": p.genero,
                         "nationality": p.pais,
                         "maritalStatus": estados[int(rng.choice(len(estados), p=pesos / pesos.sum()))]})
        while True:   # D-007: aleatorio, no correlativo, sin repetir
            n = int(rng.integers(10 ** (ids.digitos_doc - 1), 10 ** ids.digitos_doc))
            if n not in usados:
                usados.add(n)
                break
        prefijo = ids.prefijo_doc[p.pais]
        numero = f"{prefijo}{n}-{digito_verificador(n)}" if p.pais == "CHL" else f"{prefijo}{n}"
        doc.append({"personIdExternal": p.personIdExternal, "country": p.pais,
                    "cardType": "RUT" if p.pais == "CHL" else "DNI", "nationalId": numero,
                    "isPrimary": True})
    return {"PerPerson": pd.DataFrame(per), "PerPersonal": pd.DataFrame(personal),
            "PerNationalId": pd.DataFrame(doc)}


# ─────────────────────────────────────────────────────────────────────────────
# Resumen y escritura
# ─────────────────────────────────────────────────────────────────────────────
def dotacion_cierre(job: pd.DataFrame) -> list[int]:
    """Regla de dotación del diccionario §1, para cada cierre de mes de la ventana."""
    ini = np.array([d.toordinal() for d in job["startDate"]])
    fin = np.array([d.toordinal() for d in job["endDate"]])
    activo = (job["emplStatus"] == "A").to_numpy()
    resultado = []
    for i in range(0, I_FIN + 1):
        d = fin_mes(i).toordinal()
        resultado.append(int(((ini <= d) & (d <= fin) & activo).sum()))
    return resultado


def escribir(tablas: dict[str, pd.DataFrame]) -> None:
    (SALIDA / "csv").mkdir(parents=True, exist_ok=True)
    (SALIDA / "parquet").mkdir(parents=True, exist_ok=True)
    for nombre, df in tablas.items():
        # lineterminator="\n": sin esto, Windows escribe \r\n y el mismo dato tiene otra
        # huella que en Linux o macOS (D-021)
        df.to_csv(SALIDA / "csv" / f"{nombre}.csv", index=False, encoding="utf-8", lineterminator="\n")
        df.to_parquet(SALIDA / "parquet" / f"{nombre}.parquet", index=False)


def main() -> int:
    t0 = time.time()
    errores = C.validar()                       # paso 0
    if errores:
        print("CONFIGURACIÓN CON ERRORES: no se genera nada")
        for e in errores:
            print(f"  [ERROR] {e}")
        return 1
    sim = Simulacion()
    sim.crear_obras()                           # paso 2
    sim.crear_semilla()                         # pasos 3 y 4
    sim.simular()                               # paso 5
    tablas = {**tablas_catalogo(sim), **tablas_empleo(sim), **tablas_persona(sim)}  # pasos 1, 6, 7
    escribir(tablas)                            # paso 9

    dot = dotacion_cierre(tablas["EmpJob"])
    print("PA Lab · generador de datos ficticios")
    print(f"  Semilla {C.SEED} · {time.time() - t0:.0f} s · salida en data/csv y data/parquet")
    print("  Filas por tabla:")
    for nombre, df in tablas.items():
        print(f"    {nombre:<27}{len(df):>9,}".replace(",", "."))
    print(f"  Dotación de cierre (36 meses): promedio {np.mean(dot):,.0f} · "
          f"mín {min(dot):,} · máx {max(dot):,}".replace(",", "."))
    for pais in PAISES:
        f = np.array([sim.factor[pais][i] for i in range(0, I_FIN + 1)])
        rel = f / f.mean()
        # D-022: es un aviso, no un error. Mide cuánto se "impone" el ciclo a todas las obras.
        alerta = "" if C.OBRAS.factor_escala_min <= rel.min() and rel.max() <= C.OBRAS.factor_escala_max \
            else "  ← aviso: fuera de rango (D-022)"
        print(f"  Factor f(m) relativo {pais}: {rel.min():.2f} – {rel.max():.2f}{alerta}")
    print("  Siguiente paso: python generator/validar.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
