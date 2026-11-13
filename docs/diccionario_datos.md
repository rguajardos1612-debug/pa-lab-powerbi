# Diccionario de datos · Fase 1

Datos 100% ficticios de **Grupo Cordillera Sur S.A.** La estructura imita **SAP SuccessFactors Employee Central**. El objetivo es que las consultas, el modelo y las medidas que construyamos aquí se puedan replicar después contra una extracción real.

> Alcance de la Fase 1: **persona, empleo, puesto en el tiempo, remuneración y catálogos**. Las tablas de ausentismo (Fase 5) y desempeño (Fase 7) se agregan a este documento cuando llegue su fase.

---

## 1. Convenciones (valen para todas las tablas)

| Tema | Convención | Por qué |
|---|---|---|
| Nombres de tabla | Nombre de la entidad de SF (`EmpJob`, `PerPerson`…) | Así el modelo de Power BI tiene los mismos nombres que tendría con datos reales |
| Nombres de campo | Estilo OData de SF, en *camelCase* (`userId`, `startDate`, `eventReason`) | Igual que arriba; además, la API de la Fase 8 va a exponer estos mismos nombres |
| Campos que SF no trae de fábrica | Prefijo `cust_` (`cust_obraInicio`) | En SF los campos personalizados llevan ese prefijo, así queda claro qué es estándar y qué inventamos |
| Fechas | `YYYY-MM-DD`, sin hora | Evita problemas de zona horaria en Power Query |
| Registro vigente | `endDate = 9999-12-31` | Convención de SF para "sin fecha de fin" |
| Vigencia | Una fila vale **desde `startDate` hasta `endDate`, ambos incluidos** | Con eso, la fila vigente en una fecha D es la que cumple `startDate <= D <= endDate` |
| Sin solapamientos | Por cada `userId`, los períodos de `EmpJob` (y los de `EmpPayCompRecurring`) **no se solapan ni dejan huecos** entre el inicio y el término de un empleo | Cada día debe tener exactamente una fila vigente por empleo |
| Término | El último día trabajado se guarda en `EmpEmployment.endDate`. La fila de `EmpJob` con `event = TERMINATION` empieza **al día siguiente** (`endDate + 1`) y lleva `emplStatus = T` | Es la convención de Employee Central (D-008): el colaborador todavía está activo su último día |
| Monedas | CLP para Chile y PEN para Perú, sin decimales en CLP y con 2 decimales en PEN | La conversión entre monedas es tema de la Fase 6 |
| Identificador nacional | Ficticio por diseño (ver D-007 y la sección 3.3) | Regla de oro: ningún dato real |

### Regla de dotación (la usaremos en todo el proyecto)

> Un colaborador **cuenta en la dotación de la fecha D** si tiene en `EmpJob` una fila con `startDate <= D <= endDate` y `emplStatus = 'A'`.

La **dotación de cierre de mes** aplica esa regla con D = último día del mes. Este valor no se guarda en ninguna tabla: se calcula.

---

## 2. Mapa de entidades

```
                      ┌──────────────┐
                      │  PerPerson   │  1 fila por ser humano
                      └──────┬───────┘
          ┌──────────────────┼────────────────────┐
          │ 1:N (vigencia)   │ 1:N                │ 1:N
   ┌──────▼──────┐   ┌───────▼────────┐   ┌───────▼────────┐
   │ PerPersonal │   │ PerNationalId  │   │ EmpEmployment  │  1 fila por contrato
   └─────────────┘   └────────────────┘   └───────┬────────┘
                                                  │ 1:N (vigencia)
                         ┌────────────────────────┼─────────────────────────┐
                         │                        │                         │ 0..1
                  ┌──────▼──────┐        ┌────────▼─────────┐   ┌───────────▼──────────────┐
                  │   EmpJob    │        │EmpPayCompRecurring│  │ EmpEmploymentTermination │
                  └──────┬──────┘        └──────────────────┘   └──────────────────────────┘
                         │ N:1 (catálogos)
   FOCompany · FOBusinessUnit · FODivision · FODepartment · FOLocation (obra)
   FOJobCode · FOPayGrade · FOEventReason
```

**Llaves:**
- `personIdExternal` identifica a la **persona** (no cambia nunca).
- `userId` identifica al **empleo**: cada contratación nueva genera un `userId` nuevo para la misma persona. Así se modela en SF una recontratación con empleo nuevo.

---

## 3. Persona

### 3.1 `PerPerson` · grano: 1 fila por persona

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `personIdExternal` | texto (PK) | `P0000123` | Identificador de la persona. Formato `P` + 7 dígitos |
| `dateOfBirth` | fecha | `1988-04-17` | Fecha de nacimiento (no cambia en el tiempo) |
| `countryOfBirth` | texto | `CHL` | País de nacimiento, ISO-3 |

### 3.2 `PerPersonal` · grano: 1 fila por persona y período de vigencia

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `personIdExternal` | texto (FK) | `P0000123` | → `PerPerson` |
| `startDate` | fecha | `2024-03-01` | Inicio de la vigencia |
| `endDate` | fecha | `9999-12-31` | Fin de la vigencia |
| `firstName` | texto | `Camila` | Nombre (generado con Faker) |
| `lastName` | texto | `Rojas Fuentes` | Apellidos (generados con Faker) |
| `gender` | texto | `F` | `F` / `M`. Se usa para la brecha salarial en la Fase 6 |
| `nationality` | texto | `CHL` | ISO-3 |
| `maritalStatus` | texto | `S` | `S` soltero/a, `C` casado/a, `V` viudo/a, `D` divorciado/a |

> En la Fase 1 cada persona tiene una sola fila (los datos personales no cambian). La tabla igual tiene vigencia para que su forma sea la misma que en SF.

### 3.3 `PerNationalId` · grano: 1 fila por persona y documento

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `personIdExternal` | texto (FK) | `P0000123` | → `PerPerson` |
| `country` | texto | `CHL` | País que emite el documento |
| `cardType` | texto | `RUT` | `RUT` (Chile) o `DNI` (Perú) |
| `nationalId` | texto | `FCL48213907-K` | **Ficticio** (D-007): `FCL` + 8 dígitos aleatorios + `-` + dígito verificador módulo 11 para Chile; `FPE` + 8 dígitos aleatorios para Perú |
| `isPrimary` | booleano | `TRUE` | Documento principal |

> Los números son **aleatorios, no correlativos**. Así se parecen a un RUT o DNI reales en cuanto a cantidad de combinaciones posibles, y eso importa para el ejercicio de seudonimización de la Fase 10.

---

## 4. Empleo

### 4.1 `EmpEmployment` · grano: 1 fila por contrato (empleo)

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `userId` | texto (PK) | `E000456` | Identificador del empleo. Formato `E` + 6 dígitos |
| `personIdExternal` | texto (FK) | `P0000123` | → `PerPerson` |
| `startDate` | fecha | `2024-03-01` | Primer día del empleo |
| `endDate` | fecha | `2025-06-30` | **Último día trabajado**. `9999-12-31` si el empleo sigue vigente |
| `originalStartDate` | fecha | `2022-01-10` | Primer ingreso histórico de la persona al grupo (igual en todos sus empleos) |
| `isPrimary` | booleano | `TRUE` | Siempre `TRUE` en la Fase 1 (no hay empleos simultáneos) |

### 4.2 `EmpEmploymentTermination` · grano: 1 fila por empleo terminado

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `userId` | texto (PK, FK) | `E000456` | → `EmpEmployment` |
| `endDate` | fecha | `2025-06-30` | Igual a `EmpEmployment.endDate` |
| `eventReason` | texto (FK) | `TER_FIN_OBRA` | → `FOEventReason` |
| `okToRehire` | booleano | `TRUE` | Si se puede recontratar. Lo usa el generador para elegir a quién recontratar |

---

## 5. Puesto en el tiempo

### 5.1 `EmpJob` · grano: 1 fila por empleo y período de vigencia

Es la tabla central del proyecto, de donde salen la dotación, la rotación y los movimientos.

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `userId` | texto (FK) | `E000456` | → `EmpEmployment` |
| `startDate` | fecha | `2024-09-01` | Inicio de la vigencia de la fila |
| `endDate` | fecha | `2025-03-31` | Fin de la vigencia de la fila |
| `seqNumber` | entero | `1` | Desempate si hay dos eventos el mismo día (casi siempre `1`) |
| `event` | texto | `TRANSFER` | Tipo de evento (ver `FOEventReason`) |
| `eventReason` | texto (FK) | `TRF_OBRA` | → `FOEventReason` |
| `emplStatus` | texto | `A` | `A` activo, `T` terminado |
| `company` | texto (FK) | `GCS_CL` | → `FOCompany` |
| `businessUnit` | texto (FK) | `BU_EDIF` | → `FOBusinessUnit` |
| `division` | texto (FK) | `DIV_OPS` | → `FODivision` (gerencia) |
| `department` | texto (FK) | `DEP_OPS_N` | → `FODepartment` |
| `location` | texto (FK) | `OB_CL_014` | → `FOLocation` (obra, faena u oficina) |
| `jobCode` | texto (FK) | `JC_MAE2` | → `FOJobCode` |
| `payGrade` | texto (FK) | `GR_O3` | → `FOPayGrade` |
| `employeeClass` | texto | `OBR` | `OBR` obrero, `EMP` empleado |
| `contractType` | texto | `OBRA` | `OBRA` por obra o faena, `PLAZO` a plazo fijo, `INDEF` indefinido |
| `standardHours` | decimal | `44.0` | Horas semanales |
| `fte` | decimal | `1.0` | Siempre `1.0` en la Fase 1 |

**Ejemplo con el caso del Ejercicio 1** (término el 2025-06-30 y recontratación el 2025-08-15):

| userId | startDate | endDate | event | eventReason | emplStatus | location |
|---|---|---|---|---|---|---|
| E000456 | 2024-03-01 | 2025-06-30 | HIRE | HIRE_NEW | A | OB_CL_007 |
| E000456 | 2025-07-01 | 9999-12-31 | TERMINATION | TER_FIN_OBRA | T | OB_CL_007 |
| E000789 | 2025-08-15 | 9999-12-31 | REHIRE | REHIRE_OBRA | A | OB_CL_014 |

Con la regla de dotación: el 2025-06-30 está vigente la fila 1 (`A`), así que **cuenta**. El 2025-07-31 está vigente la fila 2 (`T`), así que **no cuenta**.

---

## 6. Remuneración

### 6.1 `EmpPayCompRecurring` · grano: 1 fila por empleo, componente y período de vigencia

| Campo | Tipo | Ejemplo | Descripción |
|---|---|---|---|
| `userId` | texto (FK) | `E000456` | → `EmpEmployment` |
| `startDate` | fecha | `2025-01-01` | Inicio de la vigencia |
| `endDate` | fecha | `9999-12-31` | Fin de la vigencia |
| `eventReason` | texto (FK) | `PAY_REAJ` | → `FOEventReason`. Motivo del cambio de sueldo: `HIRE_NEW`/`REHIRE_OBRA` al ingresar, `PAY_REAJ`, `PAY_MERIT` o `PRO_PROM` (ver D-009) |
| `payComponent` | texto | `SUELDO_BASE` | En la Fase 1 hay un solo componente: el sueldo base |
| `paycompvalue` | decimal | `1150000` | Monto mensual bruto |
| `currencyCode` | texto | `CLP` | Debe coincidir con la moneda de la `company` vigente |
| `frequency` | texto | `MON` | Mensual |

> Cada cambio de sueldo (reajuste, mérito, promoción) cierra una fila y abre otra, igual que en `EmpJob`. El empleo terminado conserva su última fila hasta su `EmpEmployment.endDate`.
>
> **Cómo se cierra una vigencia:** `endDate` nunca se ingresa a mano. Siempre es *el día anterior al `startDate` de la fila siguiente* del mismo `userId` (o `9999-12-31` si no hay siguiente; o `EmpEmployment.endDate` si el empleo terminó). SF calcula las fechas de fin de la misma manera.
>
> **Simplificación (D-009):** en SF, el motivo del cambio va en la entidad padre `EmpCompensation` y `EmpPayCompRecurring` guarda solo los montos. Aquí unimos las dos en una tabla para no tener un nivel extra sin uso en la Fase 1.

---

## 7. Catálogos (Foundation Objects)

| Tabla | Campos | Contenido en el generador |
|---|---|---|
| `FOCompany` | `externalCode`, `name`, `country`, `currency` | `GCS_CL` Cordillera Sur Chile S.A. (CHL, CLP); `GCS_PE` Cordillera Sur Perú S.A.C. (PER, PEN) |
| `FOBusinessUnit` | `externalCode`, `name` | Edificación, Montaje Industrial, Obras Civiles, Corporativo |
| `FODivision` | `externalCode`, `name`, `businessUnit` | Gerencias (Operaciones, Ingeniería, Prevención de Riesgos, Administración y Finanzas, Personas…) |
| `FODepartment` | `externalCode`, `name`, `division` | Departamentos dentro de cada gerencia |
| `FOLocation` | `externalCode`, `name`, `country`, `region`, `cust_tipo`, `cust_obraInicio`, `cust_obraFin` | Obras y faenas con **ciclo de vida** (inicio y fin), además de oficinas centrales (`cust_tipo = OFICINA`, sin fin) |
| `FOJobCode` | `externalCode`, `name`, `employeeClass`, `payGrade` | Cargos: Jornal, Ayudante, Maestro 2ª, Maestro 1ª, Capataz… (OBR); Analista, Ingeniero, Jefe de Obra, Gerente… (EMP) |
| `FOPayGrade` | `externalCode`, `name`, `country`, `minimo`, `medio`, `maximo` | Banda salarial por grado y país (base para el compa-ratio de la Fase 6) |
| `FOEventReason` | `externalCode`, `name`, `event`, `emplStatus`, `cust_tipoRotacion` | Ver la tabla siguiente |

### 7.1 `FOEventReason` (lista cerrada)

| externalCode | name | event | emplStatus | cust_tipoRotacion |
|---|---|---|---|---|
| `HIRE_NEW` | Nueva contratación | HIRE | A | — |
| `REHIRE_OBRA` | Recontratación para nueva obra | REHIRE | A | — |
| `TRF_OBRA` | Cambio de obra | TRANSFER | A | — |
| `TRF_AREA` | Cambio de área | TRANSFER | A | — |
| `PRO_PROM` | Promoción | PROMOTION | A | — |
| `PAY_REAJ` | Reajuste general | PAY_CHANGE | A | — |
| `PAY_MERIT` | Aumento por mérito | PAY_CHANGE | A | — |
| `TER_FIN_OBRA` | Término de obra o faena | TERMINATION | T | FIN_OBRA |
| `TER_RENUNCIA` | Renuncia voluntaria | TERMINATION | T | VOLUNTARIA |
| `TER_NEC_EMP` | Necesidades de la empresa | TERMINATION | T | INVOLUNTARIA |
| `TER_DISCIPL` | Despido disciplinario | TERMINATION | T | INVOLUNTARIA |
| `TER_MUTUO` | Mutuo acuerdo | TERMINATION | T | INVOLUNTARIA |

> `cust_tipoRotacion` es la columna que va a permitir separar, en la Fase 4, la rotación voluntaria de la rotación por término de obra.

---

## 8. Reglas de validación (se verifican en S3)

1. Todo `userId` de `EmpJob` existe en `EmpEmployment`, y todo `personIdExternal` existe en `PerPerson`.
2. Por cada `userId`, las filas de `EmpJob` no se solapan y no dejan huecos.
3. La primera fila de cada empleo tiene `event` = `HIRE` o `REHIRE` y `startDate = EmpEmployment.startDate`.
4. Un empleo es `REHIRE` si y solo si la persona ya tuvo un empleo anterior.
5. Si `EmpEmployment.endDate ≠ 9999-12-31`, existe una fila `TERMINATION` con `startDate = endDate + 1` y una fila en `EmpEmploymentTermination`.
6. Una persona no tiene dos empleos activos el mismo día.
7. `currencyCode` coincide con la moneda de la `company` vigente.
8. Nadie trabaja en una obra fuera de las fechas `cust_obraInicio` y `cust_obraFin` de esa obra.
9. `nationalId` cumple el formato ficticio y no se repite.
10. Todo `eventReason` de `EmpPayCompRecurring` es de ingreso (`HIRE`/`REHIRE`), de `PAY_CHANGE` o de `PROMOTION`. Si una fila es `PRO_PROM`, en `EmpJob` hay una promoción con el mismo `startDate`.
11. La dotación promedio mensual cumple el objetivo de D-006 y la proporción Chile/Perú queda en torno a 75/25.
