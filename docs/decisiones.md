# Registro de decisiones (ADR ligero)

Cada decisión: contexto → decisión → consecuencia. No se borran; si cambian, se agrega una nueva que la reemplaza.

## D-001 · Formato PBIP en vez de PBIX
- **Contexto:** un .pbix es binario; Git no puede mostrar qué cambió entre versiones.
- **Decisión:** todos los reportes se guardan como Power BI Project (.pbip): modelo en TMDL y reporte en PBIR (texto).
- **Consecuencia:** cada cambio en una medida DAX o en un visual queda visible en `git diff`. Los .pbix quedan excluidos en .gitignore.

## D-002 · Entorno virtual `.venv` dentro del repo, creado en Windows
- **Contexto:** el proyecto depende de librerías con versiones específicas; instalar en el Python global mezcla proyectos.
- **Decisión:** un entorno virtual por repo en `.venv/` (excluido de Git). Las dependencias directas van en `requirements.txt`; las versiones exactas en `requirements-lock.txt`.
- **Consecuencia:** el entorno se puede borrar y reconstruir en minutos con `pip install -r requirements-lock.txt`.

## D-003 · Los datos nunca se versionan
- **Contexto:** la regla inicial ("no se versionan si son pesadas") obligaba a decidir caso a caso.
- **Decisión:** nada dentro de `data/` ni de las capas del lake entra a Git. Lo versionado es el generador con semilla fija.
- **Consecuencia:** cualquier dataset se reproduce exactamente corriendo el generador. Si el generador cambia, el commit del generador documenta el cambio en los datos.

## D-004 · Python 3.14 con 3.13 como plan B
- **Contexto:** 3.14 es la versión más reciente; algunas librerías de fases futuras (API, lake) podrían tardar en soportarla.
- **Decisión:** usar 3.14. Si una librería no instala, se recrea `.venv` con 3.13 sin cambiar el código.
- **Consecuencia:** `check_env.py` acepta 3.13 con aviso.

## D-005 · Los datos se generan con fechas de vigencia (*effective dating*), no como snapshots
- **Contexto:** Employee Central guarda historial con vigencia de fecha a fecha. Una foto mensual pierde los cambios que ocurren dentro del mes y no se puede convertir de vuelta en historial.
- **Decisión:** el generador produce tablas con vigencia (`EmpJob`, `EmpPayCompRecurring`, `PerPersonal`) con la forma de SF. La dotación y cualquier snapshot se **calculan** a partir de esas tablas.
- **Consecuencia:** el modelo de la Fase 2 es más difícil, pero es el mismo problema que aparece con datos reales. La regla de dotación queda en `diccionario_datos.md` §1.

## D-006 · Definición de "~10.000 colaboradores"
- **Contexto:** "dotación en un mes" no basta, porque la dotación sube y baja con el ciclo de las obras y hay que decir de qué mes se habla. Las personas distintas en 36 meses son muchas más que la dotación.
- **Decisión:** la **dotación promedio de cierre de mes** en los 36 meses es de ≈10.000, con una oscilación por el ciclo de obras dentro de ±12 %. La distribución Chile/Perú es ≈75/25 sobre la dotación.
- **Consecuencia:** el objetivo es verificable (regla 10 del diccionario). El generador ajusta cuánto contrata para cumplirlo; el número de personas distintas es un resultado, no un parámetro.

## D-007 · Identificadores nacionales ficticios por diseño
- **Contexto:** Faker genera RUT con dígito verificador válido, que pueden coincidir con el de una persona real. Los RUT del rango 90.000.000 corresponden a empresas reales.
- **Decisión:** Chile usa `FCL` + 8 dígitos **aleatorios** + `-` + dígito verificador módulo 11. Perú usa `FPE` + 8 dígitos aleatorios. Los números no son correlativos.
- **Consecuencia:** el prefijo hace imposible confundirlos con un documento real. Al ser aleatorios, hay tantas combinaciones posibles como en un RUT real, y eso hace que el ejercicio de seudonimización de la Fase 10 sea realista. El dígito verificador permite practicar validaciones.

## D-008 · Convención de término
- **Contexto:** hay que decidir si el colaborador cuenta en la dotación de su último día. Si se elige mal, la dotación de cierre de mes sale corrida en todos los términos de fin de mes.
- **Decisión:** el último día trabajado se guarda en `EmpEmployment.endDate`. La fila `TERMINATION` de `EmpJob` empieza al día siguiente, con `emplStatus = T` (convención de Employee Central). La recontratación se registra como empleo nuevo (`userId` nuevo) con `event = REHIRE`.
- **Consecuencia:** quien termina el 30-06 cuenta en la dotación de junio. Un empleo terminado tiene al menos 2 filas en `EmpJob`.

## D-009 · El motivo del cambio de sueldo va en `EmpPayCompRecurring`
- **Contexto:** el diccionario definía los motivos `PAY_REAJ` y `PAY_MERIT`, pero ninguna tabla los usaba: un reajuste no genera fila en `EmpJob` y `EmpPayCompRecurring` no tenía columna de motivo. En SF, ese motivo va en la entidad padre `EmpCompensation`.
- **Decisión:** se agrega `eventReason` a `EmpPayCompRecurring` y no se crea `EmpCompensation` por separado (se unen en una tabla).
- **Consecuencia:** cada cambio de sueldo queda con su motivo. Si en la Fase 8 la API tiene que imitar SF exactamente, se separa en dos entidades.

## D-010 · Período de calentamiento de 24 meses, conservado como historia
- **Contexto:** al inicio de la simulación la población necesita tener antigüedad. Si se inventa a mano (por ejemplo, "35 % con menos de un año"), puede ser incoherente con las tasas de salida. Los primeros meses mostrarían entonces una rotación que baja sola y parece un patrón real.
- **Decisión:** el generador simula 24 meses antes de 2023-11 con las mismas reglas. La población semilla de ese inicio recibe una antigüedad de hasta 15 años, para que exista personal antiguo. **Los eventos del calentamiento no se borran**: quedan como historia previa, como en una extracción real de SF. Los dashboards analizan 2023-11 a 2026-10.
- **Consecuencia:** la proporción de personas nuevas, los términos, las recontrataciones y el ciclo de obras llegan estabilizados a noviembre de 2023, y la rotación de 12 meses móviles tiene datos desde el primer mes. La antigüedad de más de 2 años sigue dependiendo de la semilla, que es un supuesto. Ver el Ejercicio 3 de S2.

## D-011 · Las obras se definen por cuántas hay activas en promedio
- **Contexto:** `Obras.cantidad = 56` no aclaraba si eran simultáneas o el total del período. Con calentamiento, 56 obras en 60 meses darían ≈18 activas a la vez y ≈390 obreros por obra. En el Ejercicio 4, la estimación de S2 supuso sin decirlo que las 56 estaban activas al mismo tiempo.
- **Decisión:** el parámetro pasa a ser `activas_promedio` (CHL 30, PER 12). El generador crea tantas obras como necesite para sostener ese promedio.
- **Consecuencia:** el tamaño medio queda en ≈175 obreros por obra en Chile y ≈146 en Perú. El total de obras creadas es un resultado (≈ activas × meses / duración media, por la Ley de Little).
