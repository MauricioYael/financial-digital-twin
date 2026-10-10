# 🏦 BBVA Financial Digital Twin — Medallion Lakehouse & Data Observability

[![Architecture: Medallion](https://img.shields.io/badge/Architecture-Medallion%20%28Bronze%2C%20Silver%2C%20Gold%29-004481?style=for-the-badge)](https://github.com/)
[![Co-Branding: BBVA x Tecmilenio](https://img.shields.io/badge/Co--Branding-BBVA%20%7C%20Tecmilenio-2DCCCD?style=for-the-badge)](https://github.com/)
[![Tech Stack: Python & Streamlit](https://img.shields.io/badge/Tech%20Stack-Python%20%7C%20Pandas%20%7C%20Streamlit%20%7C%20Airflow-1464A5?style=for-the-badge)](https://github.com/)

> **Motor analítico y predictivo de salud financiera personal basado en el modelado de patrones de gasto general, simulación de escenarios ("What-If") y proyección de liquidez a 3 y 6 meses.**

---

## 🎯 Objetivo Principal

Desarrollar un **Gemelo Digital Financiero** que procese el historial transaccional del usuario para modelar sus patrones de gastos generales (fijos, variables y recurrentes). El sistema genera **proyecciones predictivas a 3 y 6 meses**, permitiendo evaluar la liquidez futura y simular variaciones de consumo antes de tomar decisiones financieras en la vida real.

---

## ⚠️ Problema Delimitado

* **Enfoque Histórico y Reactivo:** La banca personal actual se limita a mostrar saldos pasados y clasificar gastos ya realizados, sin ofrecer visibilidad del impacto futuro.
* **Desconocimiento de Liquidez Futura:** El usuario no sabe cómo evolucionará su saldo a mediano plazo si mantiene sus hábitos de consumo, impidiéndole anticipar cuellos de botella e iliquidez.
* **Ausencia de Herramientas de Simulación:** No existen mecanismos accesibles para evaluar en tiempo real el efecto de modificar gastos discrecionales o fijos sin arriesgar presupuesto real.

---

## 👤 Usuarios Target

* **Consumidor Final (B2C):** Usuarios individuales que buscan visibilidad predictiva sobre su dinero para tomar decisiones de consumo inteligentes, evitar la iliquidez y planificar metas financieras a mediano plazo (pagos fijos, viajes, ocio, etc.).

---

## 🏛️ Arquitectura Técnica (Medallion Architecture)

```text
[ Google Drive / Sheets / CSV Raw ]
          │  (Polling / Ingesta en Tiempo Real)
          ▼
    [ data/raw/ ] ──────► (Contrato de Ingesta: 6 Validaciones Previas)
          │
          ├──❌ Falla de Contrato ──► [ logs/ingestion_log.csv ] (Estado: FAILED / REJECTED)
          │
          ▼
  [ 🥉 CAPA BRONZE ] ───► (Parquet Inmutable + SHA-256 + Metadatos de Auditoría)
          │
          ▼
  [ 🥈 CAPA SILVER ] ───► (Reglas de Calidad QC-001 a QC-005: Limpieza, Tipado y Deduplicación)
          │
          ├──✅ Registros Válidos ──► [ data/silver/ ] (dim_clientes, dim_compromisos, fct_transacciones)
          └──⚠️ Registros Rotos   ──► [ data/quarantine/ ] (transacciones_cuarentena.parquet)
          │
          ▼
  [ 🥇 CAPA GOLD ] ─────► (Consolidado Analítico de Negocio: gold_cliente_mes.parquet)
          │
          ▼
  [ 💻 DASHBOARD ] ─────► Interfaz Ejecutiva BBVA x Tecmilenio (Streamlit) + Conciliación
```

| Capa / Zona | Estructura | Función Técnica |
| :--- | :--- | :--- |
| **Bronze (Raw)** | `data/bronze/*.parquet` | Ingesta de datos crudos etiquetados con hash SHA-256 para auditoría y trazabilidad inmutable. |
| **Silver (Cleaned)** | `data/silver/*.parquet` | Pipeline de limpieza, deduplicación de registros y clasificación estricta de Ingresos, Gastos Fijos y Variables. |
| **Gold (Analytics)** | `data/gold/*.parquet` | Agregaciones temporales consumidas por la calculadora predictiva, conciliación en vivo y motor de KPIs. |
| **Cuarentena** | `data/quarantine/*.parquet` | Aislamiento de transacciones corruptas con detalle técnico de error. |

---

## 🧾 Contrato de Ingesta (Validaciones Previas a Bronze)

Antes de persistir cualquier archivo en la Capa Bronze, el pipeline evalúa rigurosamente 6 condiciones de entrada:

| # | Validación | Condición de Error Detectada | Acción y Estado en Log |
| :--- | :--- | :--- | :--- |
| **V1** | Existencia | Archivo no encontrado en `data/raw/` | `FAILED` — Falla controlada explícita |
| **V2** | Formato / Extensión | Archivo no posee extensión `.csv` | `REJECTED` — Formato no soportado |
| **V3** | No vacío | Archivo de 0 bytes o sin filas | `REJECTED` — Sin datos para procesar |
| **V4** | Idempotencia | SHA-256 idéntico ya registrado en `manifest.json` | `SKIPPED` — Omite reprocesamiento redundante |
| **V5** | Esquema Mínimo | Faltan campos clave obligatorios | `REJECTED` — Esquema no compatible |
| **V6** | Tipos Legibles | Fechas o montos corruptos en origen | `WARNING` — Persiste en Bronze pero genera alerta |

---

## ⚙️ Reglas de Transformación y Calidad (Capa Silver & Cuarentena)

En la transición de Bronze a Silver se aplican las siguientes reglas de negocio:

* **QC-001 (Unicidad):** Deduplicación de claves primarias (`customer_id`, `compromiso_id`, `transaction_id`).
* **QC-002 (Integridad Monetaria):** Montos nulos o menores/iguales a cero son rechazados (`ERR_MONTO_INVALIDO`).
* **QC-003 (Integridad Referencial):** Transacciones sin un `customer_id` válido en la dimensión de clientes son desviadas (`ERR_CLIENTE_INEXISTENTE`).
* **QC-004 (Tipado y Enriquecimiento):** Estandarización a fechas ISO y etiquetado booleano de gastos recurrentes (`es_fijo`).
* **QC-005 (Estatus Operativo):** Transacciones no completadas o rechazadas son aisladas (`ERR_TX_REJECTED_OR_FAILED`).

---

## 🏆 Catálogo y Diccionario de KPIs (Capa Gold)

La capa Gold materializa el comportamiento financiero mensual en la tabla `gold_cliente_mes.parquet`. Todos los cálculos se rigen por las siguientes fórmulas y reglas defensibles:

| Campo | Tipo | Fórmula / Definición | Regla de Negocio y Caso Límite |
| :--- | :--- | :--- | :--- |
| `customer_id` | string | Identificador único del cliente | Clave primaria compuesta con `periodo`. |
| `periodo` | string | Formato `YYYY-MM` | Mes de cálculo de la agregación. |
| `ingresos_totales` | decimal | `SUM(monto)` donde `tipo = 'INGRESO'` | Excluye transferencias entre cuentas propias (`TRANSFERENCIA_PROPIA`). |
| `gastos_totales` | decimal | `SUM(monto)` donde `tipo = 'EGRESO'` | Suma de todas las salidas operativas del periodo. |
| `gastos_fijos` | decimal | `SUM(monto)` donde `es_fijo = True` | Clasificación de egresos recurrentes (rentas, servicios). |
| `flujo_neto` | decimal | `ingresos_totales - gastos_totales` | Resultado financiero neto mensual del cliente. |
| `tasa_ahorro` | decimal | `flujo_neto / ingresos_totales` | **Caso límite:** si `ingresos = 0`, se asigna `0.0` (evita división por cero / NaN). |
| `ratio_endeudamiento` | decimal | `pagos_deuda / ingresos_totales` | Mide la carga de compromisos de crédito sobre el ingreso del mes. |

---

## 📥📤 Tabla de Entradas y Salidas (I/O Table)

| Capa | Componente | Entradas (Inputs) | Transformación / Proceso | Salidas (Outputs) | Criterio de Error |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bronze** | Ingesta & Auditoría | `data/raw/*.csv` | Cálculo de hash SHA-256 y concatenación de metadatos de fecha. | `data/bronze/*.parquet` | Detener pipeline si el archivo está vacío o no coincide el hash. |
| **Silver** | Limpieza & Clasificación | `data/bronze/*.parquet` | Casting de tipos (`DATE`, `FLOAT`), deduplicación y asignación de `es_fijo`. | `data/silver/*.parquet` | Enviar filas a `data/quarantine/` si `monto` es nulo o `customer_id` no existe. |
| **Gold** | Motor de KPIs & Proyección | `data/silver/*.parquet` | Agregación mensual, cálculo de Flujo Neto, Ratio Fijo/Variable y proyección. | `data/gold/*.parquet` | Notificar advertencia si el historial del usuario es de menos de 60 días. |
| **Consumo** | Dashboard & Conciliación | `data/gold/*.parquet` | Inspector de conciliación en vivo y visualización ejecutiva. | Dashboard visual Streamlit | Mostrar advertencia en UI si no se encuentran los Parquet. |

---

## 📂 Datasets Sintéticos del Proyecto

### 1. `transacciones_dummy.csv` (Flujo de Caja Histórico)

| transaction_id | customer_id | fecha | tipo_transaccion | categoria | monto | canal | status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| T000001 | C0001 | 2026-01-02 | Ingreso | Nómina | 2850.00 | Transferencia | Completada |

### 2. `clientes_dummy.csv` (Perfil y Saldo Inicial)

| customer_id | nombre | edad | ocupacion | ingreso_mensual_base | saldo_inicial_cuenta | fecha_alta |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| C0001 | Ana | 29 | Analista de datos | 2850.00 | 1200.00 | 2024-01-15 |

### 3. `compromisos_fijos_dummy.csv` (Estructura Rígida de Gastos)

| compromiso_id | customer_id | concepto | tipo_compromiso | monto_mensual | dia_pago_mes | estado |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| K00001 | C0001 | Renta Depa | Vivienda | 670.00 | 5 | Activo |

---

## 🛠️ Registro de Decisiones Técnicas Justificadas (ADR)

**Decisión 1: Adopción del formato Parquet por capa.**
* **Motivo:** Brinda compresión eficiente, almacenamiento columnar y lectura nativa de alta velocidad.
* **Impacto:** Reduce el tamaño en disco y acelera la velocidad de respuesta en la capa analítica.

**Decisión 2: Co-Branding y Tema Institucional BBVA x Tecmilenio.**
* **Motivo:** Proporciona una experiencia de usuario corporativa de alto impacto visual con diseño *glassmorphism* y paleta oficial (`#072146`, `#2DCCCD`).
* **Impacto:** Eleva la calidad ejecutiva de la demo técnica sin sacrificar rendimiento.

**Decisión 3: Inspector de Conciliación en Vivo (Silver vs Gold).**
* **Motivo:** Permite auditar en tiempo real que la suma de transacciones en Silver coincida numéricamente con el registro de Gold.
* **Impacto:** Garantiza cero discrepancias y trazabilidad del 100% ante auditorías de datos.

**Decisión 4: Estrategia de Cuarentena para datos anómalos.**
* **Motivo:** Previene que transacciones corruptas o con valores nulos detengan el procesamiento o distorsionen las proyecciones financieras.
* **Impacto:** Mantiene la capa Silver con un 100% de consistencia.

---

## 📂 Estructura del Repositorio

```text
financial-digital-twin/
├── data/
│   ├── raw/                      # Archivos CSV crudos (origen)
│   ├── bronze/                   # Datasets Parquet inmutables + Metadatos
│   │   └── manifest.json         # Control de versiones e idempotencia por Hash SHA-256
│   ├── silver/                   # Datos limpios (dim_clientes, dim_compromisos, fct_transacciones)
│   ├── gold/                     # gold_cliente_mes.parquet (Consolidado mensual)
│   └── quarantine/               # Registros anómalos (transacciones_cuarentena.parquet)
├── docs/
│   └── data_profiling_report.md  # Reporte estadístico generado automáticamente
├── logs/
│   └── ingestion_log.csv         # Bitácora histórica estructurada de ingesta
├── reports/
│   └── validation_report.csv     # Métricas de calidad por dataset
├── src/
│   ├── dashboard.py              # Dashboard interactivo Streamlit (BBVA + Tecmilenio)
│   ├── gold_builder.py           # Transformación Silver -> Gold
│   ├── gold_validator.py         # Suite de validaciones Gold
│   ├── reconcile_gold.py         # Inspector de conciliación Silver vs Gold
│   ├── ingestion/                # Pipelines de ingesta y contrato Bronze
│   ├── transformations/          # Transformaciones Silver y Cuarentena
│   └── automation/               # File watcher y sincronizador en tiempo real
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## ⚡ Instrucciones de Arranque y Ejecución Rápida

**1. Configurar el entorno e instalar dependencias**

```bash
pip install -r requirements.txt
```

**2. Sincronización o ingesta a Bronze**

```bash
python src/ingestion/pipeline.py
```

**3. Ejecutar limpieza a capa Silver**

```bash
python src/transformations/transform_silver.py
```

**4. Generar la capa Gold (consolidado de KPIs)**

```bash
python src/gold_builder.py
```

**5. Validar calidad y conciliación**

```bash
python src/gold_validator.py
python src/reconcile_gold.py
```

**6. Iniciar el Dashboard Institucional (Streamlit)**

```bash
streamlit run src/dashboard.py
```

Accede desde tu navegador en: <http://localhost:8501>

---

## 📊 Módulos del Dashboard Institucional

* **🏠 Dashboard Principal:** Resumen ejecutivo con micro-ondas en tarjetas KPI, tasa de calidad, distribución de registros por capa y estado operativo en tiempo real.
* **📊 Calidad de Datos:** Matriz interactiva por dataset (Bronze vs. Silver vs. Errores) con porcentaje de salud.
* **🏆 Capa Gold (KPIs):** Consolidado mensual analítico con filtros dinámicos por cliente/periodo y evolución gráfica de Flujo Neto, Ingresos y Egresos.
* **🔎 Conciliación Silver vs Gold:** Herramienta de auditoría que comprueba la igualdad numérica exacta entre `fct_transacciones` y `gold_cliente_mes`.
* **🛡️ Cuarentena:** Inspección detallada de registros aislados con trazabilidad de código de error.