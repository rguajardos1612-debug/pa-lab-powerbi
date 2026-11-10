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
- Rotación de obreros dominada por término de obra/faena; rotación voluntaria de empleados concentrada en los primeros 12 meses.
- Ausentismo con estacionalidad invernal y diferencias por obra.
- Brecha salarial por género en algunos cargos, no en todos.
- Distribución de desempeño con sesgo de indulgencia en ciertas gerencias.

## Licenciamiento (decisión)

- **Fases 0–10:** solo Power BI Desktop (gratis). No se requiere pagar nada.
- **Fase 11:** cuenta de prueba de Microsoft 365 E5 (crea una cuenta *@onmicrosoft.com* con Power BI Pro). Activarla justo al iniciar la Fase 11, porque la prueba es temporal.
- No usar la cuenta corporativa para experimentos.

## Estado actual

- **Fase actual:** 0 — Setup
- **Próxima sesión:** S1
- **Bloqueos:** ninguno

## Bitácora

| Sesión | Fecha | Qué se hizo | Pendiente para la siguiente |
|---|---|---|---|
| S0 | 2026-11-10 | Definición del proyecto, alcance y roadmap | Crear repo y proyecto en Claude; conectar carpeta |
