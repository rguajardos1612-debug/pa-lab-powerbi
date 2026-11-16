# PA Lab · Power BI People Analytics

Proyecto personal de aprendizaje: construir dashboards de People Analytics en Power BI con datos 100% ficticios, para luego replicar las prácticas en un rol real.

## Contexto de la empresa ficticia

| Atributo | Valor |
|---|---|
| Nombre | **Grupo Cordillera Sur S.A.** (ficticio) |
| Rubro | Ingeniería y construcción (edificación, montaje industrial, obras civiles) |
| Dotación | ~10.000 colaboradores |
| Países | Chile (~75%) y Perú (~25%) |
| Monedas | CLP, PEN (+ UF para referencias Chile) |
| Poblaciones | Obreros (contrato por obra/faena, alta rotación) y Empleados (indefinidos) |
| Historia | 36 meses (snapshots mensuales + eventos) |

**Regla de oro:** en este repositorio nunca entra un dato real de ninguna empresa.

## Cómo trabajamos

- **Una sesión = un chat nuevo** dentro del proyecto de Claude.
- Cada sesión parte leyendo este archivo y termina actualizándolo (estado + bitácora) con un commit.
- Orden fijo en cada tema: **concepto → ejemplo → código completo → ejercicio → verificación**.
- El código se entrega como archivo completo, no como fragmentos para pegar.
- Horario: 18:00–22:00 (Chile). Bloque sugerido: 2 × 1:45 h con pausa de 15 min.
- Ritmo: hasta 5 días por semana, planificado como **3 sesiones de contenido nuevo + hasta 2 de práctica** (ejercicios sin ayuda, repaso, rehacer lo que no salió).
- Regla de avance: no se pasa de fase sin resolver solo el ejercicio de cierre de la fase anterior.
- Duración estimada: ~7–8 semanas (22 sesiones de contenido + práctica).

## Estructura del repositorio

```
pa-lab-powerbi/
├── ROADMAP.md              ← este archivo (estado y bitácora)
├── README.md
├── docs/                   ← diccionario de datos, glosario de KPIs, decisiones
├── generator/              ← Python: generador de datos ficticios
├── api/                    ← Fase 8: API ficticia (FastAPI)
├── lake/                   ← Fase 9: bronze / silver / gold (Parquet)
├── security/               ← Fase 10: pseudonimización, cifrado, secretos
├── data/                   ← salidas del generador (no se versionan si son pesadas)
└── powerbi/                ← proyectos .pbip (versionables con Git)
```

## Fases

Las sesiones son de ~4 h. El orden pone primero los dashboards (DAX es la habilidad central y hoy está en nivel inicial) y después la ingeniería de datos que los alimenta.

| Fase | Tema | Sesiones | Lo que aprendes | Entregable |
|---|---|---|---|---|
| 0 | Setup | S1 | Estructura de repo, entorno virtual, compatibilidad Python 3.14, formato PBIP | Repo listo y primer commit |
| 1 | Datos ficticios | S2–S3 | Diccionario de datos con estructura tipo SuccessFactors (persona, puesto, eventos, compensación); patrones plantados | Generador + datasets validados |
| 2 | Power Query + modelo | S4–S5 | ETL en Power Query (M), modelo estrella, tabla calendario, relaciones y granularidad | Modelo semántico base |
| 3 | DAX I + Dotación | S6–S7 | Medidas vs columnas, CALCULATE, contexto de filtro, snapshots | **Dashboard Dotación** |
| 4 | DAX II + Rotación | S8–S9 | Inteligencia de tiempo, rotación voluntaria vs término de obra, rotación 12 meses móviles | **Dashboard Rotación** |
| 5 | Ausentismo | S10 | Tasas de ausentismo, días perdidos, licencias (Chile) vs descansos médicos (Perú) | **Dashboard Ausentismo** |
| 6 | Demografía + Compensaciones | S11–S12 | Pirámides, brecha salarial ajustada, compa-ratio, multimoneda (CLP/PEN) | **Dashboards Demografía y Compensaciones** |
| 7 | Desempeño (PMGM) | S13 | Ciclo de metas, distribución de calificaciones, matriz 9-box, cruce con rotación | **Dashboard Desempeño** |
| 8 | API ficticia | S14–S15 | API REST local (FastAPI), paginación, autenticación por token, conector Web de Power BI | API + conexión desde Power BI |
| 9 | Data lake local | S16–S17 | Arquitectura medallion (bronze/silver/gold), Parquet, DuckDB, cargas incrementales | Lake local alimentando el modelo |
| 10 | Seguridad | S18–S19 | Pseudonimización (hash de RUT/DNI), cifrado de archivos, gestión de secretos, RLS y OLS | Pipeline seguro + RLS por país/gerencia |
| 11 | Power BI Service | S20–S21 | Publicación, workspaces, RLS en producción, actualización programada, gateway | Reportes publicados (cuenta de prueba) |
| 12 | Cierre y réplica | S22 | Checklist de gobernanza y plan para llevar lo aprendido al rol real | Plan de réplica |

### Patrones que se plantan en los datos (para que haya algo que descubrir)

- Dotación que sube y baja con el ciclo de vida de las obras.
- Rotación de obreros dominada por término de obra/faena. Renuncia temprana de empleados: la **tasa mensual** de renuncia con ≤12 meses de antigüedad es ≈3,3 veces la de quienes tienen más (se mide como tasa condicionada a la antigüedad, no como proporción de las renuncias; S2).
- Ausentismo con estacionalidad invernal y diferencias por obra.
- Brecha salarial por género en algunos cargos, no en todos.
- Distribución de desempeño con sesgo de indulgencia en ciertas gerencias.

## Licenciamiento (decisión)

- **Fases 0–10:** solo Power BI Desktop (gratis). No se requiere pagar nada.
- **Fase 11:** cuenta de prueba de Microsoft 365 E5 (crea una cuenta *@onmicrosoft.com* con Power BI Pro). Activarla justo al iniciar la Fase 11, porque la prueba es temporal.
- No usar la cuenta corporativa para experimentos.

## Estado actual

- **Fase actual:** 2 — Power Query + modelo (Fase 1 cerrada en S3: ejercicio de cierre aprobado)
- **Próxima sesión:** S4 — importar las tablas de `data/` a Power Query (M), tipos de datos y fechas con vigencia; empezar el modelo estrella
- **Cómo regenerar los datos:** `python generator\generar.py` → `python generator\validar.py` (debe terminar en `VALIDACIÓN OK ✔`). Después de cualquier cambio al generador: `python generator\reproducibilidad.py` y `python generator\sabotaje.py`
- **Datos de referencia (semilla 20261113):** 15 tablas, `EmpJob` 104.295 filas, `EmpEmployment` 48.101, `PerPerson` 39.127. Idénticos en Windows y Linux. CSV alcanza para Power Query (pregunta abierta de S2 resuelta); Parquet queda para la Fase 9
- **Documentos base para S4:** `docs/diccionario_datos.md` (regla de dotación §1, vigencias), decisiones D-005, D-008, D-017 (bandas con vigencia), D-019 (`seqNumber`), D-022 (olas sincronizadas)
- **Entorno:** Python 3.14.10 en `.venv`; numpy 2.5.4, pandas 3.1.1, pyarrow 26.0.1, Faker 40.54.0 (ver `requirements-lock.txt`)
- **Ojo en S4:** (1) `9999-12-31` es "vigente, sin fin conocido": cualquier duración o filtro por `endDate` se acota a la fecha de corte (2026-10-31), como en R8. (2) Los códigos (`A`/`T`, `TER_FIN_OBRA`) se copian del diccionario; en S2 y S3 se escribieron de memoria (`Active`, `Terminated`). (3) Separar siempre prueba exacta (una fila basta) de estimación con tolerancia. (4) Practicar con un ejemplo hecho a mano de filas con `seqNumber > 1` (D-019). (5) Antes de explicar un número, medirlo
- **Preguntas abiertas:** ver §4 de `docs/diseno_generador.md` (antigüedad para recontratados, sueldo en REHIRE, nacimientos de obras que siguen el ciclo)
- **Bloqueos:** ninguno

## Bitácora

| Sesión | Fecha | Qué se hizo | Pendiente para la siguiente |
|---|---|---|---|
| S0 | 2026-11-10 | Definición del proyecto, alcance y roadmap | Crear repo y proyecto en Claude; conectar carpeta |
| S1 | 2026-11-10 | Estructura del repo, `.gitignore` / `.gitattributes`, `.venv` con Python 3.14, `requirements.txt` + lock, `check_env.py` (5/5 OK), decisiones D-001 a D-004, primer PBIP (`powerbi/S01_prueba`) con tabla `_Medidas` y medida `Prueba = 1` en TMDL/PBIR. **Errores:** instalé en el Python global por no activar `.venv` (lo detectó la ruta de pip); lock guardado en UTF-16 con `>`; en C confundí activar con reconstruir — corregido: `py -3.14 -m venv .venv` → activar → `pip install -r requirements-lock.txt`. | S2: antes de correr Python, confirmar `(.venv)` en el prompt |
| S2 | 2026-11-13 | Diccionario de datos tipo Employee Central (`docs/diccionario_datos.md`: 7 tablas con nombres OData, catálogos, `FOEventReason` con `cust_tipoRotacion`, regla de dotación, 11 reglas de validación). Decisiones D-005 (*effective dating*), D-006 (≈10.000 = dotación promedio de cierre de mes, ±12 %, 75/25), D-007 (IDs ficticios `FCL`/`FPE` aleatorios), D-008 (término: fila TERMINATION al día siguiente del último día), D-009 (`eventReason` en `EmpPayCompRecurring`), D-010 (calentamiento de 24 meses conservado como historia), D-011 (obras activas en promedio). `generator/config.py` con validación (probado: error de pesos detectado). `docs/diseno_generador.md` con algoritmo y 15 valores esperados calculados en los ejercicios de flujo (Ley de Little). **Errores:** en EmpJob junté contratación y término en una fila (1 evento = 1 fila); usé códigos inventados (`NEW_HIRE`, `Active`) en vez de los del catálogo, lo que rompería la relación en Power BI; corrí comandos desde `System32` sin `cd` y reaccioné reconstruyendo el entorno en vez de leer el error; supuse 56 obras simultáneas; justifiqué con supuestos (costo de regenerar) que contradicen D-003. | S3: implementar el generador y verificarlo contra §3 de `diseno_generador.md` |
| S3 | 2026-11-16 | Generador implementado: `generator/generar.py` (simulación por eventos → tablas con vigencia), `validar.py` (R1–R10, valores de §3, balances exactos, identidad de personas A + B + C, brecha), `reproducibilidad.py` y `sabotaje.py` (4 de 4 sabotajes detectados). Todo OK en Windows. Decisiones D-012 a D-023: empleados sin fin de obra (D-012), traslado de obreros como parámetro (D-013), manda el seno de D-006 con factor f(m) (D-014, D-020), promociones por escalera y con vacante (D-015), sueldo de promoción por posición en la banda (D-016), bandas con vigencia anual (D-017), `TRF_OFICINA` (D-018), un evento de `EmpJob` por día (D-019), no depender del orden de un `set` (D-021), f(m) como aviso: el ciclo está impuesto a todas las obras (D-022), tolerancia de la brecha con z = 3 (D-023). Ejercicio de cierre de la Fase 1 aprobado (P0002642). **Errores míos:** la fórmula de G5 rompía la banda o la brecha; el rango de f(m) no tenía unidades; `sorted(set(...))` con empates hacía el generador no reproducible; R8 trató 9999-12-31 como fecha real; el Ejercicio 3 partió de una premisa falsa (el traslado sí funcionaba). **Errores tuyos:** Ej. 1: aplicaste el 35 % de REHIRE a todos los ingresos y no sumaste A + B; Ej. 2: `Terminated` en vez de `T` (otra vez), faltó `eventReason` en pagos, "2 filas" el mismo día rompe las vigencias; aprobaste G5 sin detectar el problema; te saltaste dos veces un ejercicio; Ej. 3: tu propuesta no se probó con datos, contradecía D-011 y aceptaste mi premisa sin medirla; Ej. 4: confundiste prueba exacta con tolerancia (el balance falla con una sola fila). | S4: Power Query; leer el "Ojo en S4" del Estado actual |
