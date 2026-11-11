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
