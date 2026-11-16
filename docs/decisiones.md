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

## D-012 · Los empleados no terminan por fin de obra
- **Contexto:** el 45 % de los empleados trabaja en obras, pero `TER_FIN_OBRA` solo estaba pensado para obreros. Faltaba decir qué pasa con un empleado cuando su obra cierra.
- **Decisión:** los empleados (`EMP`) nunca usan `TER_FIN_OBRA`. Cuando su obra baja o termina, se trasladan (`TRF_OBRA`) a otra obra activa del mismo país o a una oficina.
- **Consecuencia:** se mantiene válido el Ejercicio 3 (≈37 ingresos al mes, que no consideran fin de obra). La dotación de empleados queda estable (≈3.000) y toda la oscilación de D-006 la absorben los obreros (±17 %), así que la proporción 70/30 se cumple en promedio pero mes a mes va de ≈67/33 a ≈73/27.

## D-013 · El traslado de obreros entre obras es un parámetro
- **Contexto:** `TRF_OBRA` para obreros se iba a "resolver en el código". Eso deja un número escondido en la lógica (rompe el Principio 1) justo en la variable más incierta de §3: los términos por fin de obra (300–490 al mes).
- **Decisión:** `Movimientos.obr_fraccion_traslado = 0.20` es la fracción máxima de los sobrantes de una obra en bajada que pasa a otra obra del mismo país que tenga déficit. El resto termina con `TER_FIN_OBRA`.
- **Consecuencia:** el efecto que baja la cifra de fin de obra (nota de §3 del diseño) queda explícito y versionado.

## D-014 · La curva de D-006 manda sobre los trapecios de las obras
- **Contexto:** si cada obra sigue su trapecio exacto, la suma no da un ciclo de ±12 % cada 18 meses. Las dos cosas no se pueden cumplir a la vez.
- **Decisión:** el objetivo mensual de obreros sale de la curva de D-006. Cada mes, la dotación de cada obra es su trapecio por un factor común f(m) = objetivo de obreros ÷ suma de trapecios. El generador informa si f(m) sale de `[factor_escala_min, factor_escala_max]` (0,70–1,30).
- **Consecuencia:** se cumple D-006 y cada obra mantiene la forma de su ciclo. Un f(m) fuera de rango es señal de que la curva regular se ve artificial (responde la pregunta abierta de §4 del diseño).

## D-015 · Promociones por escalera y solo con vacante
- **Contexto:** con una probabilidad fija, los cargos altos crecen sin límite. Por ejemplo, ≈135 subgerentes al 0,8 % mensual dan ≈13 promociones al año a Gerente, frente a ≈9 salidas al año de 75 gerentes.
- **Decisión:** `ESCALERA` en `config.py` define el cargo siguiente de cada cargo (CAP y GER no se promueven). `obr_promocion` y `emp_promocion` son **probabilidades máximas**: solo se promueve si el cargo de destino tiene vacante respecto de su peso en `CARGOS`.
- **Consecuencia:** la pirámide se mantiene cerca de los pesos de configuración. La tasa real de promoción es un resultado y será menor que el parámetro.

## D-016 · Sueldo de promoción: se conserva la posición en la banda y la brecha es del cargo de destino
- **Contexto:** con "anterior × 1,12 y mínimo de banda", una promoción ING → JOB siempre queda bajo el mínimo de JOB. Si después se aplica la brecha de destino, la mujer cae bajo la banda; si el mínimo se aplica al final, la brecha desaparece. Además, la brecha de origen se arrastraba a cargos sin brecha (ING → JOB → SUB).
- **Decisión:** z = sueldo ÷ (medio de origen × (1 + brecha de origen)). Nuevo sueldo = máx(anterior × (1 + `promocion_pct`); medio de destino × z × (1 + brecha de destino)). Los medios son los de la fecha de la promoción (D-017).
- **Consecuencia:** la brecha pertenece al cargo, no se hereda. `promocion_pct` funciona como piso (todos los saltos de la escalera son de +15 % o más). En los cargos con brecha, las mujeres con z < ≈0,89 quedan bajo el mínimo de banda. **Se deja así a propósito**: es un hallazgo observable en el compa-ratio de la Fase 6, no un error.

## D-017 · Las bandas salariales tienen vigencia anual
- **Contexto:** los sueldos suben con el reajuste durante 60 meses. Con bandas fijas, el compa-ratio promedio de 2026 quedaría en ≈1,25 y mediría reajustes acumulados en vez de posición en la banda.
- **Decisión:** `sueldo_medio` de `config.py` es el valor de la banda en 2026-10. Para fechas anteriores, el medio se reconstruye descontando los reajustes de cada año. `FOPayGrade` pasa a tener `startDate`/`endDate` (una fila por grado, país y año de reajuste), como los Foundation Objects con vigencia en SF.
- **Consecuencia:** el compa-ratio de cualquier fecha se calcula contra la banda vigente en esa fecha, lo que suma un *join* por vigencia más en el modelo de la Fase 2. El mérito sigue haciendo subir el compa-ratio con la antigüedad: eso es esperado, no una deriva.

## D-018 · Motivo `TRF_OFICINA` para el traslado de obra a oficina
- **Contexto:** D-012 manda a la oficina a algunos empleados cuando su obra cierra, pero el único motivo disponible era `TRF_OBRA` ("Cambio de obra"), que no describe ese movimiento (detectado en el Ejercicio 2 de S3).
- **Decisión:** se agrega `TRF_OFICINA` · Traslado de obra a oficina · `TRANSFER` · `A`. Cuando una obra cierra, los cargos de obra (`CARGOS_EN_OBRA`: ING, JOB, PRV) pasan a otra obra activa del país con `TRF_OBRA`. El cargo de ajuste (ADM) y los casos en que no queda ninguna obra activa pasan a la oficina con `TRF_OFICINA`.
- **Consecuencia:** el catálogo tiene 13 motivos. En la Fase 4 se pueden separar los traslados entre obras de los traslados a oficina.

## D-019 · Como máximo un evento de `EmpJob` por empleo y día
- **Contexto:** si un empleo tiene dos eventos el mismo día (por ejemplo, traslado y promoción), la regla "endDate = día anterior al siguiente startDate" deja la primera fila con `endDate` menor que su `startDate`. Con la convención de SF (las dos filas vigentes ese día, se desempata con `seqNumber`), dos filas cumplen `startDate <= D <= endDate` y se rompe la regla 2 del diccionario.
- **Decisión:** el generador nunca produce dos eventos de `EmpJob` el mismo día para un empleo: quien ya tuvo un traslado ese día no se promueve ni cambia de área ese mes. `seqNumber` es siempre 1. Los cambios de sueldo del mismo día (reajuste y promoción) se juntan en una sola fila con el último motivo.
- **Consecuencia:** el modelo de la Fase 2 no necesita desempatar. Como en una extracción real de SF sí aparecen filas con `seqNumber > 1`, en la Fase 2 se practica con un ejemplo construido a mano (quedarse con el mayor `seqNumber` por `userId` y `startDate`).

## D-020 · El rango de f(m) se evalúa sobre el factor relativo
- **Contexto:** D-014 definió f(m) = objetivo de obreros ÷ suma de trapecios. Ese valor tiene unidades (obreros por unidad de tamaño de obra), así que compararlo con 0,70–1,30 no tiene sentido.
- **Decisión:** el rango se aplica a f(m) ÷ promedio de f en los 36 meses.
- **Consecuencia:** un valor de 1,30 significa que ese mes las obras tienen 30 % más gente que su forma "normal".

## D-021 · Ningún resultado puede depender del orden de un `set`
- **Contexto:** en S3, dos ejecuciones del generador con la misma semilla dieron datos distintos (48.008 contra 48.101 empleos). La causa fue `sorted(set(...))` en las promociones: CAP y ANA tienen el mismo sueldo medio en Perú (4.800 PEN), y con ese empate el orden lo decidía el `set`. Python cambia en cada ejecución el orden interno de los textos (`PYTHONHASHSEED`), así que el orden de las promociones también cambiaba.
- **Decisión:** en el generador, cualquier colección que se recorra y afecte el resultado es una lista o un `dict` (conservan el orden de inserción). Un `set` solo se usa para preguntar si un elemento está. `generator/reproducibilidad.py` corre el generador con dos `PYTHONHASHSEED` distintos y compara las 15 tablas byte a byte.
- **Consecuencia:** D-003 queda verificable con una prueba y no solo como intención. La prueba se corre después de cada cambio al generador, antes del commit.
- **Verificación entre entornos (S3):** Windows (Python 3.14, numpy 2.5, pandas 3.1) y Linux (Python 3.10, numpy 2.2, pandas 2.3) generaron las 15 tablas con el mismo contenido. La huella solo difería porque pandas en Windows escribe fin de línea `\r\n`. Desde entonces los CSV se escriben con `\n`, así la huella es la misma en cualquier sistema.

## D-022 · El rango de f(m) es un aviso: el ciclo está impuesto a todas las obras
- **Contexto:** en S3, f(m) relativo salió de 0,74 a 1,33 en Chile y de 0,56 a 1,40 en Perú. Hay dos causas. (1) Las obras nacen sin seguir el ciclo, así que la suma de trapecios es plana en promedio y f tiene que oscilar ±17 % por construcción; con el rango 0,70–1,30 queda solo ±13 % de margen para el ruido. (2) Con nacimientos de Poisson, la cantidad de obras activas varía ≈1/√A (18 % en Chile, 29 % en Perú). Con 8 semillas: subir Perú a 20 obras no resolvió nada (0/8 dentro de rango) y además contradice D-011. Hacer que las obras nazcan de forma regular y siguiendo el ciclo arregló Chile (8/8), pero no Perú.
- **Decisión:** el rango de f(m) se informa como **aviso**, no como error. Se acepta el hallazgo: la oscilación de D-006 está *impuesta* a todas las obras (todas suben y bajan a la vez), no *causada* por ellas. El valor esperado de fin de obra pasa a ser ≈476 al mes (rango mensual 213–761). Se valida el mecanismo, no el monto: traslados ÷ sobrantes ≈ `obr_fraccion_traslado`.
- **Consecuencia:** en los datos se van a ver olas de contratación y despido sincronizadas entre obras. Los nacimientos de obras que siguen el ciclo quedan pendientes (§4 del diseño), para cuando la Fase 3 muestre si eso se ve artificial.

## D-023 · La tolerancia de la brecha usa 3 errores estándar
- **Contexto:** con máx(2 pp; 2 × error estándar) se prueban 14 cargos en cada validación. Aunque el generador sea perfecto, la probabilidad de que al menos un cargo falle por azar es 1 − 0,9545¹⁴ ≈ 48 % (comparaciones múltiples; Ejercicio 4 de S3).
- **Decisión:** `Patrones.tolerancia_brecha_z = 3.0`. La probabilidad de una falsa alarma en alguno de los 14 cargos baja a ≈3,7 %. Se descartó dejar en "aviso" los fallos de uno o dos cargos: "sin patrón sistemático" no es una regla que se pueda programar.
- **Consecuencia:** menos poder en los cargos chicos. En GER (≈22 mujeres) la tolerancia queda en ≈±7 pp, así que una filtración de brecha de −6 % no se detectaría ahí. Se acepta, porque la brecha se planta en cargos grandes (ING, JOB, JEF), donde la tolerancia sigue cerca de ±3 pp.
