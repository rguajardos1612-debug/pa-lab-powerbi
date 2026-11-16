# Diseño del generador · Fase 1

Cómo se construye el generador de datos ficticios (código en S3) y qué valores deben salir. Los parámetros están en `generator/config.py`; las tablas, en `docs/diccionario_datos.md`.

---

## 1. Principios

| # | Principio | Qué evita |
|---|---|---|
| 1 | **Parámetros separados de la lógica.** Todo número que define a la empresa está en `config.py`; la lógica no tiene números escritos a mano | Cambiar el código para ajustar una tasa |
| 2 | **Semilla fija** (D-003). Con la misma semilla y el mismo código salen los mismos datos | Versionar datos; resultados que no se pueden reproducir |
| 3 | **Primero eventos, después filas.** La simulación produce una lista de eventos (quién, qué, cuándo, motivo) y las tablas con vigencia se derivan de ella al final | Solapamientos y huecos: las fechas de fin nunca se inventan, salen del orden de los eventos |
| 4 | **La validación de la configuración va primero.** `validar()` corre antes de generar | Errores silenciosos (por ejemplo, pesos que se normalizan sin avisar) |
| 5 | **Las magnitudes de flujo son resultados, no parámetros.** La antigüedad, las personas distintas y el total de obras se derivan de las tasas | Pedir combinaciones imposibles (Ejercicio 3: "35 % con 12 meses o menos") |
| 6 | **Calentamiento conservado como historia** (D-010) | Una rotación que baja sola al inicio; ventanas móviles incompletas |

---

## 2. Algoritmo

```
0. validar(config)                     → si hay errores, se detiene
1. Catálogos                           → FOCompany, FOBusinessUnit, FODivision, FODepartment,
                                          FOJobCode, FOPayGrade, FOEventReason
2. Obras                               → FOLocation con cust_obraInicio / cust_obraFin,
                                          suficientes para sostener Obras.activas_promedio (D-011)
3. Dotación objetivo por mes           → curva total 10.000 ± 12 % (ciclo de 18 meses),
                                          repartida por país, clase, obra y oficina;
                                          cada obra sigue su trapecio (subida, peak, bajada)
4. Población semilla (mes −24)         → personas con antigüedad de hasta 15 años
5. Simulación mes a mes (−24 … +35):
     a. Términos      → fin de obra (cuando la obra baja o termina) y probabilidades de Movimientos
     b. Movimientos   → transferencias a obras que crecen, promociones, cambio de área
     c. Remuneración  → reajuste (enero), mérito (abril, solo empleados), aumento por promoción
     d. Contrataciones → cierran la brecha con la dotación objetivo:
                         primero REHIRE (obreros con okToRehire y pausa cumplida), luego HIRE
6. Lista de eventos → tablas           → EmpEmployment, EmpEmploymentTermination, EmpJob,
                                          EmpPayCompRecurring (endDate = siguiente startDate − 1)
7. Personas                            → PerPerson, PerPersonal, PerNationalId (D-007)
8. Validación de datos                 → las 11 reglas del diccionario y los valores esperados (§3)
9. Escritura                           → data/ (CSV y Parquet; no se versiona, D-003)
```

**Orden dentro del mes:** primero los términos y después las contrataciones, porque contratar es cubrir lo que falta para llegar al objetivo.

---

## 3. Valores esperados (S3 los verifica)

Salen de los Ejercicios 3 y 4 de S2: son cálculos de **flujo estable**, no reglas exactas. Las tolerancias son amplias a propósito; si un valor queda fuera, primero se busca la causa, porque un número fuera de rango no siempre es un error.

| Indicador (ventana de 36 meses) | Esperado | Tolerancia | De dónde sale |
|---|---|---|---|
| Dotación promedio de cierre de mes | 10.000 | ±3 % | D-006 |
| Mínimo y máximo de dotación mensual | ≈8.800 y ≈11.200 | ±5 % | D-006 |
| Chile / Perú (sobre la dotación) | 75 / 25 | ±2 pp | D-006 |
| Obreros / Empleados | 70 / 30 | ±2 pp | config |
| **Empleados:** ingresos mensuales | ≈37 | 30–45 | Ejercicio 3 (punto de equilibrio) |
| **Empleados:** rotación anual | ≈15 % | 12–18 % | Ejercicio 3 |
| **Empleados:** proporción con 12 meses o menos | ≈13 % | 10–17 % | Ejercicio 3 |
| **Empleados:** tasa de renuncia ≤12 m ÷ tasa >12 m | ≈3,3 | 2,5–4,0 | Patrón plantado (definición de S2) |
| **Obreros:** rotación anual sin fin de obra | ≈30 % | 25–35 % | Ejercicio 4 |
| **Obreros:** términos por fin de obra al mes | ≈476 (S3); rango mensual 213–761 | aviso fuera de 300–600 | Ejercicio 4 y D-022; ver nota |
| **Obreros:** traslados ÷ sobrantes (traslado + fin de obra) | `obr_fraccion_traslado` (20 %) | ±3 pp | D-013 |
| **Obreros:** REHIRE ÷ términos por fin de obra | ≈35 % | 25–40 % | config |
| Personas distintas en la ventana | ≈26.000 | 20.000–33.000 | Ejercicio 4 |
| Personas distintas en todo el dataset (con calentamiento) | ≈37.000 | — | Ejercicio 4 más 24 meses |
| Brecha de género en `JC_ING`, `JC_JOB`, `JC_JEF` | −8 %, −10 %, −6 % | máx(2 pp; 3 × error estándar) (D-023) | Patrón plantado |
| Brecha de género en los demás cargos | 0 % | máx(2 pp; 3 × error estándar) (D-023) | Patrón plantado |

**Nota sobre el fin de obra.** La estimación de S2 fue ≈375 al mes (7.000 obreros ÷ 19 meses). Hay dos efectos que la mueven en sentidos opuestos:
- **La sube:** por el trapecio, la dotación promedio de una obra es ≈75 % de su peak, pero salen todos los puestos del peak. Eso da ≈7.000 ÷ (0,75 × 19) ≈ 490.
- **La baja:** parte de los obreros de las obras en bajada se transfieren (`TRF_OBRA`) a obras en subida y no terminan.
- **Medido en S3 (D-022):** los sobrantes brutos son ≈591 al mes, sobre el techo de 490, porque el ciclo de D-006 se impone a todas las obras a la vez (f(m)). El traslado efectivo es 19,5 % de los sobrantes y deja el fin de obra en ≈476.

---

## 4. Preguntas abiertas

| Pregunta | Cuándo se resuelve |
|---|---|
| ¿La antigüedad al salir se mide desde `EmpEmployment.startDate` o desde `originalStartDate`? Para un recontratado, cambia la tasa de renuncia temprana | Fase 4 (definición de la medida) |
| ¿Cuántas filas tendrá `EmpJob`? Esto define si conviene CSV o Parquet en Power Query | S3, al correr el generador |
| ¿La curva de dotación objetivo sigue un ciclo regular (seno) o la suma de obras con fechas al azar? | S3: manda el seno (D-014); f(m) sale de rango y queda como aviso (D-022) |
| ¿Un REHIRE conserva su posición en la banda o sortea una nueva? Hoy sortea una nueva: en S3, P0002642 subió 16 % siendo Jornal en los dos empleos | Fase 6 (compa-ratio) |
| ¿Conviene que las obras nazcan siguiendo el ciclo (nacimientos regulares con amplitud y desfase)? | Si los dashboards de la Fase 3 muestran olas de contratación y despido sincronizadas que se vean artificiales |
