# pa-lab-powerbi

Laboratorio personal de People Analytics en Power BI con datos **100% ficticios** de *Grupo Cordillera Sur S.A.* (constructora ficticia, Chile y Perú).

- Plan, estado y bitácora: [ROADMAP.md](ROADMAP.md)
- Decisiones técnicas: [docs/decisiones.md](docs/decisiones.md)

## Puesta en marcha (Windows / PowerShell)

```powershell
cd C:\Data\pa-lab-powerbi
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-lock.txt     # versiones exactas (reproducible)
python generator\check_env.py
```

Si se agrega una librería a `requirements.txt`: instalarla y regenerar el lock con
`pip freeze | Set-Content -Encoding utf8 requirements-lock.txt`.

> Regla de oro: en este repositorio nunca entra un dato real de ninguna empresa.
