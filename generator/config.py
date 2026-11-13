"""
config.py — Parámetros del generador de datos ficticios (Fase 1).

Todo lo que define "cómo es" Grupo Cordillera Sur S.A. vive en este archivo.
La lógica del generador (S3) solo lee estos valores; no tiene números escritos a mano.

Uso (desde la raíz del repo, con .venv activado):
    python generator/config.py

Muestra un resumen de la configuración y la valida. Termina con código 0 si es
consistente y 1 si hay errores.

Referencias: docs/diccionario_datos.md y docs/decisiones.md (D-003, D-005 a D-009).
Todos los valores son inventados. Ninguno viene de una empresa real.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import date

# ─────────────────────────────────────────────────────────────────────────────
# 1. Reproducibilidad (D-003)
# ─────────────────────────────────────────────────────────────────────────────
# Con la misma semilla y el mismo código, el generador produce exactamente los
# mismos datos. Si cambia la semilla, los datos cambian aunque el código no cambie.
SEED: int = 20261113


# ─────────────────────────────────────────────────────────────────────────────
# 2. Período
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Periodo:
    primer_mes: date = date(2023, 11, 1)  # primer día del primer mes simulado
    meses: int = 36                       # termina en octubre de 2026
    # Calentamiento (D-010): meses simulados ANTES de primer_mes. Sus eventos se
    # conservan como historia previa (igual que en una extracción real de SF); los
    # dashboards analizan solo los 36 meses. Así, en noviembre de 2023 la antigüedad
    # ya es coherente con las tasas y la rotación de 12 meses móviles tiene datos.
    meses_calentamiento: int = 24
    # Antigüedad de la población semilla (al inicio del calentamiento), en años.
    # Evita que nadie tenga más de 2 años de antigüedad en 2023.
    antiguedad_semilla_max_anios: int = 15


# ─────────────────────────────────────────────────────────────────────────────
# 3. Dotación objetivo (D-006)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Dotacion:
    promedio_cierre_mes: int = 10_000     # promedio de los 36 cierres de mes
    oscilacion: float = 0.12              # ± sobre el promedio, por el ciclo de obras
    ciclo_meses: int = 18                 # meses entre dos peaks de dotación
    tolerancia_promedio: float = 0.03     # para validar en S3: el promedio real debe quedar a ±3 %
    participacion_pais: dict[str, float] = field(
        default_factory=lambda: {"CHL": 0.75, "PER": 0.25}
    )
    participacion_clase: dict[str, float] = field(
        default_factory=lambda: {"OBR": 0.70, "EMP": 0.30}
    )
    # Proporción de empleados que trabajan en una obra (jefes de obra, ingenieros,
    # prevencionistas, administrativos de obra). El resto trabaja en oficinas.
    empleados_en_obra: float = 0.45


# ─────────────────────────────────────────────────────────────────────────────
# 4. Organización (catálogos que el generador convierte en FO*)
# ─────────────────────────────────────────────────────────────────────────────
COMPANIAS: dict[str, dict[str, str]] = {
    "GCS_CL": {"name": "Cordillera Sur Chile S.A.", "country": "CHL", "currency": "CLP"},
    "GCS_PE": {"name": "Cordillera Sur Perú S.A.C.", "country": "PER", "currency": "PEN"},
}

UNIDADES_NEGOCIO: dict[str, str] = {
    "BU_EDIF": "Edificación",
    "BU_MONT": "Montaje Industrial",
    "BU_OOCC": "Obras Civiles",
    "BU_CORP": "Corporativo",
}

GERENCIAS: dict[str, str] = {
    "DIV_OPS": "Gerencia de Operaciones",
    "DIV_ING": "Gerencia de Ingeniería",
    "DIV_PRV": "Gerencia de Prevención de Riesgos",
    "DIV_AYF": "Gerencia de Administración y Finanzas",
    "DIV_PER": "Gerencia de Personas",
}


@dataclass(frozen=True)
class Obras:
    """Obras y faenas: cada una tiene un ciclo de vida (FOLocation.cust_obraInicio/Fin)."""
    # Obras ACTIVAS EN PROMEDIO en un mes (D-011), no el total del período. El
    # generador crea tantas obras como necesite (calentamiento + 36 meses) para
    # mantener este promedio; por la Ley de Little, el total es ≈ activas × meses / duración.
    activas_promedio: dict[str, int] = field(default_factory=lambda: {"CHL": 30, "PER": 12})
    # Cómo se reparten las obras entre unidades de negocio (Corporativo no tiene obras)
    mix_unidad: dict[str, float] = field(
        default_factory=lambda: {"BU_EDIF": 0.50, "BU_MONT": 0.25, "BU_OOCC": 0.25}
    )
    duracion_min_meses: int = 8
    duracion_max_meses: int = 30
    # Forma de la dotación de una obra: sube, se mantiene en su peak y baja (trapecio)
    fraccion_subida: float = 0.25
    fraccion_bajada: float = 0.25
    # El tamaño del peak de cada obra NO se fija aquí: el generador lo escala
    # para que la suma de todas las obras más las oficinas cumpla D-006.


# ─────────────────────────────────────────────────────────────────────────────
# 5. Cargos y remuneraciones (FOJobCode, FOPayGrade)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Cargo:
    codigo: str          # FOJobCode.externalCode
    nombre: str
    clase: str           # OBR / EMP
    grado: str           # FOPayGrade.externalCode
    peso: float          # participación dentro de su clase (los pesos de una clase suman 1)
    sueldo_medio: dict[str, int]  # mensual bruto, punto medio de la banda por país


CARGOS: tuple[Cargo, ...] = (
    # ── Obreros ──────────────────────────────────────────────────────────────
    Cargo("JC_JOR",    "Jornal",                 "OBR", "GR_O1", 0.30, {"CHL":   650_000, "PER":  2_400}),
    Cargo("JC_AYU",    "Ayudante",               "OBR", "GR_O2", 0.25, {"CHL":   750_000, "PER":  2_700}),
    Cargo("JC_MAE2",   "Maestro 2ª",             "OBR", "GR_O3", 0.22, {"CHL":   950_000, "PER":  3_200}),
    Cargo("JC_MAE1",   "Maestro 1ª",             "OBR", "GR_O4", 0.15, {"CHL": 1_150_000, "PER":  3_800}),
    Cargo("JC_CAP",    "Capataz",                "OBR", "GR_O5", 0.08, {"CHL": 1_450_000, "PER":  4_800}),
    # ── Empleados ────────────────────────────────────────────────────────────
    Cargo("JC_ADM",    "Administrativo",         "EMP", "GR_E1", 0.180, {"CHL":   900_000, "PER":  3_000}),
    Cargo("JC_ANA",    "Analista",               "EMP", "GR_E2", 0.200, {"CHL": 1_400_000, "PER":  4_800}),
    Cargo("JC_ANA_SR", "Analista Sr",            "EMP", "GR_E3", 0.100, {"CHL": 1_800_000, "PER":  6_200}),
    Cargo("JC_PRV",    "Prevencionista",         "EMP", "GR_E3", 0.100, {"CHL": 1_700_000, "PER":  5_800}),
    Cargo("JC_ING",    "Ingeniero de Terreno",   "EMP", "GR_E3", 0.170, {"CHL": 2_000_000, "PER":  7_000}),
    Cargo("JC_JOB",    "Jefe de Obra",           "EMP", "GR_E4", 0.100, {"CHL": 3_200_000, "PER": 11_000}),
    Cargo("JC_JEF",    "Jefe de Área",           "EMP", "GR_E4", 0.080, {"CHL": 3_000_000, "PER": 10_500}),
    Cargo("JC_SUB",    "Subgerente",             "EMP", "GR_E5", 0.045, {"CHL": 4_800_000, "PER": 16_500}),
    Cargo("JC_GER",    "Gerente",                "EMP", "GR_E6", 0.025, {"CHL": 7_500_000, "PER": 26_000}),
)


@dataclass(frozen=True)
class Remuneracion:
    # Banda de cada grado: mínimo y máximo como fracción del punto medio
    banda_min: float = 0.80
    banda_max: float = 1.20
    # Dispersión del sueldo de ingreso alrededor del punto medio (desviación estándar)
    dispersion_ingreso: float = 0.08
    # Reajuste general: un mes fijo al año, para todos los activos (eventReason PAY_REAJ)
    reajuste_mes: int = 1
    reajuste_pct: dict[str, float] = field(default_factory=lambda: {"CHL": 0.045, "PER": 0.030})
    # Mérito: solo empleados, un mes fijo al año (eventReason PAY_MERIT)
    merito_mes: int = 4
    merito_fraccion_elegible: float = 0.60
    merito_pct_medio: float = 0.035
    # Promoción: aumento al pasar al cargo siguiente (eventReason PRO_PROM)
    promocion_pct: float = 0.12


# ─────────────────────────────────────────────────────────────────────────────
# 6. Movimientos (probabilidades MENSUALES por colaborador activo)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Movimientos:
    # Términos de obreros. El término por fin de obra no es una probabilidad:
    # ocurre cuando la obra termina (o baja su dotación en el tramo de bajada).
    obr_renuncia: float = 0.020
    obr_nec_empresa: float = 0.004
    obr_disciplinario: float = 0.001
    # Términos de empleados: la renuncia depende de la antigüedad (patrón plantado)
    emp_renuncia_hasta_12m: float = 0.020
    emp_renuncia_desde_13m: float = 0.006
    emp_nec_empresa: float = 0.003
    emp_disciplinario: float = 0.0005
    emp_mutuo_acuerdo: float = 0.001
    # Recontratación de obreros que terminaron por fin de obra (REHIRE_OBRA)
    obr_prob_recontratacion: float = 0.35
    obr_pausa_min_meses: int = 1
    obr_pausa_max_meses: int = 3
    # Probabilidad de quedar con okToRehire = TRUE según el motivo de término
    ok_recontratar: dict[str, float] = field(
        default_factory=lambda: {
            "TER_FIN_OBRA": 1.00,
            "TER_RENUNCIA": 0.70,
            "TER_NEC_EMP": 0.90,
            "TER_MUTUO": 0.80,
            "TER_DISCIPL": 0.00,
        }
    )
    # Promociones y transferencias
    obr_promocion: float = 0.010
    emp_promocion: float = 0.008
    emp_transferencia_area: float = 0.004
    # Los obreros cambian de obra (TRF_OBRA) cuando su obra baja dotación y otra
    # obra del mismo país necesita gente; el generador lo resuelve en S3.


# ─────────────────────────────────────────────────────────────────────────────
# 7. Demografía (PerPerson, PerPersonal)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Demografia:
    proporcion_mujeres: dict[str, float] = field(default_factory=lambda: {"OBR": 0.06, "EMP": 0.35})
    edad_ingreso_min: int = 18
    edad_ingreso_max: int = 65
    edad_ingreso_media: dict[str, int] = field(default_factory=lambda: {"OBR": 36, "EMP": 33})
    edad_ingreso_desv: int = 9
    locale_faker: dict[str, str] = field(default_factory=lambda: {"CHL": "es_CL", "PER": "es_ES"})


# ─────────────────────────────────────────────────────────────────────────────
# 8. Patrones plantados (para que haya algo que descubrir)
# ─────────────────────────────────────────────────────────────────────────────
# Solo los de la Fase 1: dotación, rotación y remuneraciones. El ausentismo
# (Fase 5) y el desempeño (Fase 7) se agregan cuando llegue su fase.
@dataclass(frozen=True)
class Patrones:
    # Brecha de género: sueldo de las mujeres respecto al de los hombres, SOLO en
    # estos cargos. En los demás cargos la brecha es 0.
    brecha_genero: dict[str, float] = field(
        default_factory=lambda: {"JC_ING": -0.08, "JC_JOB": -0.10, "JC_JEF": -0.06}
    )
    # Los otros dos patrones de la Fase 1 ya están en otras secciones:
    #   - el ciclo de obras en Dotacion.oscilacion / ciclo_meses
    #   - la renuncia temprana de empleados en Movimientos.emp_renuncia_hasta_12m


# ─────────────────────────────────────────────────────────────────────────────
# 9. Identificadores (D-007)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Identificadores:
    prefijo_persona: str = "P"
    digitos_persona: int = 7
    prefijo_empleo: str = "E"
    digitos_empleo: int = 6
    prefijo_doc: dict[str, str] = field(default_factory=lambda: {"CHL": "FCL", "PER": "FPE"})
    digitos_doc: int = 8
    fecha_abierta: date = date(9999, 12, 31)


# ─────────────────────────────────────────────────────────────────────────────
# Instancias que usa el generador
# ─────────────────────────────────────────────────────────────────────────────
PERIODO = Periodo()
DOTACION = Dotacion()
OBRAS = Obras()
REMUNERACION = Remuneracion()
MOVIMIENTOS = Movimientos()
DEMOGRAFIA = Demografia()
PATRONES = Patrones()
IDS = Identificadores()


# ─────────────────────────────────────────────────────────────────────────────
# Validación
# ─────────────────────────────────────────────────────────────────────────────
def _suma_uno(nombre: str, valores: dict[str, float] | list[float], errores: list[str]) -> None:
    total = sum(valores.values()) if isinstance(valores, dict) else sum(valores)
    if abs(total - 1.0) > 1e-9:
        errores.append(f"{nombre}: suma {total:.4f}, debe sumar 1")


def _probabilidad(nombre: str, valor: float, errores: list[str]) -> None:
    if not 0.0 <= valor <= 1.0:
        errores.append(f"{nombre}: {valor} no está entre 0 y 1")


def validar() -> list[str]:
    """Devuelve la lista de errores. Si está vacía, la configuración es consistente."""
    errores: list[str] = []

    # Período
    if PERIODO.primer_mes.day != 1:
        errores.append("Periodo.primer_mes debe ser el día 1 de un mes")
    if PERIODO.meses < 12:
        errores.append("Periodo.meses debe ser al menos 12 (la rotación móvil necesita 12 meses)")
    if PERIODO.meses_calentamiento < 12:
        errores.append("Periodo.meses_calentamiento debe ser al menos 12 (D-010)")
    if PERIODO.antiguedad_semilla_max_anios < 1:
        errores.append("Periodo.antiguedad_semilla_max_anios debe ser al menos 1")

    # Dotación
    _suma_uno("Dotacion.participacion_pais", DOTACION.participacion_pais, errores)
    _suma_uno("Dotacion.participacion_clase", DOTACION.participacion_clase, errores)
    _probabilidad("Dotacion.oscilacion", DOTACION.oscilacion, errores)
    _probabilidad("Dotacion.empleados_en_obra", DOTACION.empleados_en_obra, errores)
    paises_compania = {c["country"] for c in COMPANIAS.values()}
    if set(DOTACION.participacion_pais) != paises_compania:
        errores.append("Los países de Dotacion.participacion_pais no coinciden con COMPANIAS")

    # Obras
    _suma_uno("Obras.mix_unidad", OBRAS.mix_unidad, errores)
    for bu in OBRAS.mix_unidad:
        if bu not in UNIDADES_NEGOCIO:
            errores.append(f"Obras.mix_unidad: {bu} no existe en UNIDADES_NEGOCIO")
    if set(OBRAS.activas_promedio) != paises_compania:
        errores.append("Los países de Obras.activas_promedio no coinciden con COMPANIAS")
    if not OBRAS.duracion_min_meses <= OBRAS.duracion_max_meses:
        errores.append("Obras: duracion_min_meses es mayor que duracion_max_meses")
    if OBRAS.fraccion_subida + OBRAS.fraccion_bajada >= 1.0:
        errores.append("Obras: subida + bajada debe ser menor que 1 (si no, la obra no tiene peak)")

    # Cargos
    codigos = [c.codigo for c in CARGOS]
    if len(codigos) != len(set(codigos)):
        errores.append("CARGOS: hay códigos repetidos")
    for clase in DOTACION.participacion_clase:
        pesos = [c.peso for c in CARGOS if c.clase == clase]
        if not pesos:
            errores.append(f"CARGOS: no hay cargos de la clase {clase}")
        else:
            _suma_uno(f"CARGOS (pesos clase {clase})", pesos, errores)
    for c in CARGOS:
        if c.clase not in DOTACION.participacion_clase:
            errores.append(f"{c.codigo}: clase {c.clase} desconocida")
        if set(c.sueldo_medio) != paises_compania:
            errores.append(f"{c.codigo}: sueldo_medio debe tener un valor por país")
        if any(v <= 0 for v in c.sueldo_medio.values()):
            errores.append(f"{c.codigo}: sueldo_medio debe ser positivo")

    # Remuneración
    if not 0 < REMUNERACION.banda_min < 1 < REMUNERACION.banda_max:
        errores.append("Remuneracion: debe cumplirse 0 < banda_min < 1 < banda_max")
    for nombre in ("reajuste_mes", "merito_mes"):
        if not 1 <= getattr(REMUNERACION, nombre) <= 12:
            errores.append(f"Remuneracion.{nombre} debe estar entre 1 y 12")
    _probabilidad("Remuneracion.merito_fraccion_elegible", REMUNERACION.merito_fraccion_elegible, errores)

    # Movimientos
    for nombre, valor in vars(MOVIMIENTOS).items():
        if isinstance(valor, float):
            _probabilidad(f"Movimientos.{nombre}", valor, errores)
    for motivo, valor in MOVIMIENTOS.ok_recontratar.items():
        _probabilidad(f"Movimientos.ok_recontratar[{motivo}]", valor, errores)
    if not 1 <= MOVIMIENTOS.obr_pausa_min_meses <= MOVIMIENTOS.obr_pausa_max_meses:
        errores.append("Movimientos: debe cumplirse 1 <= obr_pausa_min_meses <= obr_pausa_max_meses")

    # Demografía
    for clase, valor in DEMOGRAFIA.proporcion_mujeres.items():
        _probabilidad(f"Demografia.proporcion_mujeres[{clase}]", valor, errores)
    if not DEMOGRAFIA.edad_ingreso_min < DEMOGRAFIA.edad_ingreso_max:
        errores.append("Demografia: edad_ingreso_min debe ser menor que edad_ingreso_max")

    # Patrones
    for codigo, brecha in PATRONES.brecha_genero.items():
        if codigo not in codigos:
            errores.append(f"Patrones.brecha_genero: {codigo} no existe en CARGOS")
        if not -0.5 < brecha <= 0:
            errores.append(f"Patrones.brecha_genero[{codigo}]: {brecha} fuera de rango (-0.5, 0]")
    cargos_sin_brecha = [c for c in codigos if c not in PATRONES.brecha_genero]
    if not cargos_sin_brecha:
        errores.append("Patrones.brecha_genero: el patrón es 'en algunos cargos, no en todos'")

    return errores


def resumen() -> None:
    p, d = PERIODO, DOTACION
    ultimo_mes_idx = p.primer_mes.month - 1 + p.meses - 1
    ultimo = date(p.primer_mes.year + ultimo_mes_idx // 12, ultimo_mes_idx % 12 + 1, 1)
    print("PA Lab · configuración del generador")
    print(f"  Semilla ............. {SEED}")
    print(f"  Período ............. {p.primer_mes:%Y-%m} a {ultimo:%Y-%m} ({p.meses} meses)")
    print(f"  Calentamiento ....... {p.meses_calentamiento} meses previos (se conservan como historia)")
    print(f"  Dotación promedio ... {d.promedio_cierre_mes:,} "
          f"(rango {d.promedio_cierre_mes * (1 - d.oscilacion):,.0f}–"
          f"{d.promedio_cierre_mes * (1 + d.oscilacion):,.0f})".replace(",", "."))
    for pais, part in d.participacion_pais.items():
        print(f"    {pais} ............. {part:.0%} ≈ {d.promedio_cierre_mes * part:,.0f}".replace(",", "."))
    for clase, part in d.participacion_clase.items():
        print(f"    {clase} ............. {part:.0%} ≈ {d.promedio_cierre_mes * part:,.0f}".replace(",", "."))
    print(f"  Obras activas ....... {sum(OBRAS.activas_promedio.values())} en promedio "
          f"({', '.join(f'{k} {v}' for k, v in OBRAS.activas_promedio.items())})")
    print(f"  Cargos .............. {len(CARGOS)} "
          f"({sum(c.clase == 'OBR' for c in CARGOS)} OBR, {sum(c.clase == 'EMP' for c in CARGOS)} EMP)")
    print(f"  Brecha plantada en .. {', '.join(PATRONES.brecha_genero)}")


def main() -> int:
    resumen()
    errores = validar()
    print()
    if errores:
        print(f"CONFIGURACIÓN CON {len(errores)} ERROR(ES) ✘")
        for e in errores:
            print(f"  [ERROR] {e}")
        return 1
    print("CONFIGURACIÓN VÁLIDA ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
