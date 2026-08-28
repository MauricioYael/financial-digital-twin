# 💎 Financial Digital Twin

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

## 🏗️ Arquitectura Técnica (Medallion Architecture)

| Capa / Zona | Estructura | Función Técnica |
| :--- | :--- | :--- |
| **Bronze (Raw)** | `data/bronze/*.parquet` | Ingesta de datos sintéticos crudos etiquetados con hash **SHA-256** para auditoría y trazabilidad inmutable. |
| **Silver (Cleaned)** | `data/silver/*.parquet` | Pipeline automatizado de limpieza, deduplicación de registros y clasificación estricta de **Ingresos**, **Gastos Fijos** y **Gastos Variables**. |
| **Gold (Analytics)** | `data/gold/*.parquet` | Agregaciones temporales consumidas por la calculadora predictiva y el motor de KPIs. |

---

## 🧩 Descripción de Componentes del Pipeline

1. **Módulo de Ingesta & Auditoría:** Captura los archivos CSV sintéticos en `data/raw/`, genera la firma digital **SHA-256** por archivo y agrega la etiqueta de auditoría `fecha_ingesta`.
2. **Capa Bronze (Raw Storage):** Almacena la copia inmutable de los datos de origen en formato `.parquet` comprimido sin aplicar transformaciones.
3. **Capa Silver (Cleansing & Enrichment):** Normaliza tipos de datos, elimina duplicados, valida la integridad referencial de `customer_id` y clasifica cada transacción con la bandera booleana `es_fijo`. Los registros inválidos se aíslan en `data/cuarentena/`.
4. **Capa Gold (Analytics & Forecasting):** Agrega métricas mensuales consolidadas y calcula la proyección determinista de liquidez a 3 y 6 meses.
5. **Motor DuckDB:** Ejecuta consultas SQL sobre los archivos Parquet en disco a alta velocidad sin requerir un servidor dedicado.
6. **Dashboard Interactivo:** Interfaz gráfica para visualizar la curva inercial y simular ajustes de variabilidad de gasto mediante controles tipo slider.

---

## 📥📤 Tabla de Entradas y Salidas (I/O Table)

| Capa | Componente | Entradas (Inputs) | Transformación / Proceso | Salidas (Outputs) | Criterio de Error |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bronze** | Ingesta & Auditoría | `data/raw/*.csv` | Cálculo de hash SHA-256 y concatenación de metadatos de fecha. | `data/bronze/*.parquet` | Detener pipeline si el archivo está vacío o no coincide el hash. |
| **Silver** | Limpieza & Clasificación | `data/bronze/*.parquet` | Casting de tipos (`DATE`, `FLOAT`), deduplicación y asignación de `es_fijo`. | `data/silver/*.parquet` | Enviar filas a `data/cuarentena/` si `monto` es nulo o `customer_id` no existe. |
| **Gold** | Motor de KPIs & Proyección | `data/silver/*.parquet` | Agregación mensual, cálculo de Flujo Neto, Ratio Fijo/Variable y proyección inercial. | `data/gold/*.parquet` | Notificar advertencia si el historial del usuario es de menos de 60 días. |
| **Consumo** | Dashboard & Simulador | `data/gold/*.parquet` | Consulta SQL mediante DuckDB y aplicación del factor de ajuste. | Dashboard visual (*Línea Base vs. Simulación*) | Mostrar mensaje en UI si DuckDB no encuentra las tablas Gold. |

---

## 🚀 Scope del MVP (Foco y Validación Ágil)

El MVP valida la hipótesis central mediante 3 pilares clave:

1. **Ingesta y Clasificación (Bronze / Silver):** Procesamiento de archivos CSV sintéticos con trazabilidad SHA-256 y etiquetado automático de gastos fijos vs. variables.
2. **Motor Predictivo + "What-If" (Analytics):** Calculadora de tendencia inercial a **3 y 6 meses** combinada con un motor de simulación para recalcular la curva de liquidez ante ajustes de gasto variable.
3. **Dashboard Comparativo (Frontend):** Interfaz gráfica desarrollada en **Next.js** / **Streamlit** que sobrepone la *Línea Base Inercial* contra la *Línea Simulada*.

---

## 📊 Catálogo Centralizado de KPIs

### 🔹 KPI 1: Flujo Neto Mensual
* **Definición:** Diferencia neta mensual entre ingresos y gastos totales (Ingresos - Gastos).
* **Campos de origen:** `monto`, `tipo_movimiento`, `fecha_operacion`.
* **Periodicidad:** Mensual.
* **Regla de calidad:** Excluir transferencias entre cuentas propias y eliminar registros con montos nulos o negativos.
* **Interpretación de negocio:** Indica si el usuario opera en superávit (capacidad de ahorro) o en déficit (pérdida de liquidez).

---

### 🔹 KPI 2: Ratio de Gastos Fijos vs. Variables
* **Definición:** Porcentaje de gastos variables y discrecionales respecto al total de egresos del mes.
* **Campos de origen:** `monto`, `tipo_movimiento`, `es_fijo`.
* **Periodicidad:** Mensual.
* **Regla de calidad:** Garantizar que el 100% de las transacciones de gasto estén etiquetadas correctamente como fijas o variables.
* **Interpretación de negocio:** Mide la elasticidad del presupuesto y determina qué tanto margen de maniobra tiene el simulador para aplicar recortes.

---

### 🔹 KPI 3: Liquidez Futura Proyectada (3 y 6 Meses)
* **Definición:** Estimación del saldo disponible en cuenta a 90 y 180 días combinando el consumo inercial con los ajustes del simulador.
* **Campos de origen:** `saldo_inicial`, `monto`, `tipo_movimiento`, `es_fijo`, factor de ajuste.
* **Periodicidad:** Proyección a 3 y 6 meses.
* **Regla de calidad:** Requerir un historial mínimo de 60 días continuos de datos sintéticos sin vacíos transaccionales.
* **Interpretación de negocio:** Detecta con anticipación el riesgo de iliquidez y advierte al usuario cuándo se quedará sin dinero si no modifica sus hábitos.

---

## 📂 Datasets Sintéticos del Proyecto

### 1. `transacciones_dummy.csv` (Flujo de Caja Histórico)

| `transaction_id` | `customer_id` | `fecha` | `tipo_transaccion` | `categoria` | `monto` | `canal` | `estatus` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `T000001` | `C0001` | `2026-01-02` | Ingreso | Nómina | 2850.00 | Transferencia | Completada |
| `T000002` | `C0001` | `2026-01-04` | Gasto | Vivienda | 670.01 | Domiciliación | Completada |

* **Qué representa:** Registro transaccional diario a nivel evento (granularidad máxima) acumulado durante 6 a 12 meses.
* **Cómo conecta:** Se vincula mediante `customer_id` con el cliente y usa `fecha` para construir las series de tiempo.
* **Qué tan confiable:** 0% de nulos en llaves o montos, tipos de datos fuertemente tipados y sin duplicados.

---

### 2. `clientes_dummy.csv` (Perfil y Saldo Inicial)

| `customer_id` | `nombre` | `edad` | `ocupacion` | `ingreso_mensual_base` | `saldo_inicial_cuenta` | `fecha_alta` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `C0001` | Ana | 29 | Analista de datos | 2850.00 | 1200.00 | `2024-01-15` |

* **Qué representa:** Perfil maestro del usuario (1 fila por cliente) y balance inicial de su cuenta.
* **Cómo conecta:** Actúa como catálogo maestro mediante la llave primaria `customer_id`.
* **Qué tan confiable:** Valores numéricos no negativos y validación de unicidad en `customer_id`.

---

### 3. `compromisos_fijos_dummy.csv` (Estructura Rígida de Gastos)

| `compromiso_id` | `customer_id` | `concepto` | `tipo_compromiso` | `monto_mensual` | `dia_pago_mes` | `estado` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `K00001` | `C0001` | Renta Depa | Vivienda | 670.00 | 5 | Activo |

* **Qué representa:** Obligaciones financieras periódicas (renta, servicios, suscripciones, pagos de deuda).
* **Cómo conecta:** Se enlaza con `customer_id` y permite validar las transacciones etiquetadas como `es_fijo = True`.
* **Qué tan confiable:** Montos estrictamente mayores a cero y días de pago válidos entre 1 y 31.

---

## 🛠️ Registro de Decisiones Técnicas Justificadas (ADR)

* **Decisión 1: Adopción del formato Parquet por capa.**
  * *Motivo:* Brinda compresión eficiente, almacenamiento columnar y lectura nativa de alta velocidad desde Python y DuckDB.
  * *Impacto:* Reduce el tamaño en disco y acelera la velocidad de respuesta en la capa analítica.
  * *Riesgo:* Imposibilidad de inspeccionar los datos directamente con un editor de texto plano.
* **Decisión 2: Orquestación mediante Script ejecutable en Python (`pipeline.py`).**
  * *Motivo:* Evita la sobrecarga de infraestructura y complejidad operativa de herramientas como Apache Airflow en la fase de MVP.
  * *Impacto:* Permite ejecutar todo el procesamiento end-to-end de manera determinista con un solo comando.
  * *Riesgo:* Falta de una interfaz web nativa para monitorear ejecuciones programadas.
* **Decisión 3: Estrategia de Cuarentena para datos anómalos.**
  * *Motivo:* Previene que transacciones corruptas o con valores nulos detengan el procesamiento o distorsionen las proyecciones financieras.
  * *Impacto:* Mantiene la capa Silver con un 100% de consistencia y auditoría.
  * *Riesgo:* Subestimación del gasto si una cantidad significativa de registros se desvía a cuarentena sin revisión.
* **Decisión 4: Motor de analítica con DuckDB incorporado.**
  * *Motivo:* Permite ejecutar SQL complejo directamente sobre archivos Parquet locales sin requerir un servidor de base de datos como PostgreSQL.
  * *Impacto:* Arquitectura de consulta ligera, rápida y zero-config.
  * *Riesgo:* Limitado a la memoria RAM del equipo ejecutor.

---

## ⚡ Riesgos y Mitigaciones

1. **Heterogeneidad de Formatos:**
   * *Riesgo:* Estructuras variables de datos bancarios o fuentes sintéticas.
   * *Mitigación:* Definición de esquemas de validación estrictos en la Capa Bronze.
2. **Requerimientos de Cómputo para IA/Modelos:**
   * *Riesgo:* Carga alta de procesamiento local al simular escenarios.
   * *Mitigación:* Implementación de fórmulas deterministas y agregaciones optimizadas en DuckDB / Parquet.
3. **Inconsistencia en Datos de Entrada:**
   * *Riesgo:* Vacíos históricos que distorsionen la tendencia inercial.
   * *Mitigación:* Filtrado en Capa Silver requiriendo un piso mínimo de 60 días de historial continuo.

---

## 🚀 Instrucciones de Arranque y Demo Local

### 1. Configurar el entorno
```bash
cp .env.example .env
pip install -r requirements.txt
```

### 2. Ejecutar la simulación del Pipeline (Raw -> Bronze)
```bash
python src/ingestion/ingest_bronze.py
```

### 3. Verificar los artefactos creados (Bronze & Logs)
```bash
# Ver los archivos Parquet generados en Capa Bronze
ls -la data/bronze/

# Revisar el log de trazabilidad y hash SHA-256
cat logs/ingestion.log
```

### 4. Ejecución alternativa con Docker Compose
```bash
docker-compose up --build
```
---

 ## 🏗️ 1. Arquitectura del Pipeline
 ```text
[ Google Drive / Sheets ]
          │  (Polling en tiempo real cada 5 segundos)
          ▼
    [ data/raw/ ] ──────► (Contrato de Ingesta: 6 Validaciones Previas)
          │
          ├──❌ Falla de Contrato ──► [ logs/ingestion_log.csv ] (Estado: FAILED / REJECTED)
          │
          ▼
  [ data/bronze/ ] ─────► (Parquet Inmutable + SHA-256 + Metadatos de Auditoría)
          │
          ├─────────────────────────► [ docs/data_profiling_report.md ] (Perfilado Estadístico)
          ▼
[ src/transformations/ ] ─► (Reglas de Calidad QC-001 a QC-005)
          │
          ├──✅ Registros Válidos ──► [ data/silver/ ] (dim_clientes, dim_compromisos, fct_transacciones)
          └──⚠️ Registros Rotos   ──► [ data/quarantine/ ] (transacciones_cuarentena.parquet)
```
 ## 🧾 2. Contrato de Ingesta (Validaciones Previas a Bronze)
Antes de persistir cualquier archivo en la Capa Bronze, el pipeline evalúa rigurosamente 6 condiciones de entrada:

| `#`|  `Validación` |  `Condicion de Error Detectada`|  `Acción y Estado en Log`|
| :---| :--- | :--- | :--- |
|  `V1`| `Existencia ` | `Archivo no encontrado en data/raw ` | `FAILED — Falla controlada explícita` | 
|  `V2`| `Formato / Extensión ` | `Archivo no posee extensión .csv` | `REJECTED — Formato no soportado` | 
|  `V3`| `No vacío ` | `Archivo de 0 bytes o sin filas ` | `REJECTED — Sin datos para procesar` | 
|  `V4`| `Idempotencia ` | `SHA-256 idéntico ya registrado en manifest.json` | `SKIPPED — Omite reprocesamiento redundante` | 
|  `V5`| `Esquema Minimo ` | `Faltan campos clave obligatorios` | `REJECTED — Esquema no compatible` | 
|  `V6`| `Tipos Legibles ` | `Fechas o montos corruptos en origen ` | `WARNING — Persiste en Bronze pero genera alerta` | 

## 3. Reglas de transformación y Calidad (Capa Silver & Cuarentena)
En la transición de Bronze a Silver se aplican las siguientes reglas de negocios.
* **QC-001 (Unicidad)**: Deduplicación de claves primarias (customer_id, compromiso_id, transaction_id).
* **QC-002 (Integridad Monetaria)**: Montos nulos o menores/iguales a cero son rechazados (ERR_INVALID_OR_NEGATIVE_AMOUNT).
* **QC-003 (Integridad Referencial)**: Transacciones sin un customer_id válido en la dimensión de clientes son desviadas (ERR_ORPHAN_CUSTOMER_ID).
* **QC-004 (Tipado y Enriquecimiento)**: Estandarización a fechas ISO y etiquetado booleano de gastos recurrentes (es_fijo).
* **QC-005 (Estatus Operativo)**: Transacciones no completadas o rechazadas son aisladas (ERR_TX_REJECTED_OR_FAILED).

## 4. Modos de Ejecución y Automatización
### 🔹 Modo 1: Sincronización en Tiempo real con Google Drive (Recomendado)
Monitorea cada una de las hojas de Google Sheats en la nube cada 5 segundos. Cualquier cambio hecho en el navegador se descarga y procesa de forma inmediata en todas las capas:
```bash
py src/automation/live_drive_watcher.py
```

### 🔹 Modo 2: Centinela Local (File Watcher)
Monitorea la carpeta data/raw/ . Al pegar o guardar un nuevo archivo CSV, dispara todo el flujo de forma automatica
```bash
py src/automation/auto_watcher.py
```

### 🔹 Modo 3: Ejecución Manual Orquestada (End-to-End)
Ejecuta todo el pipeline (Ingesta ➔ Perfilado ➔ Silver/Cuarentena) en un solo paso:
```bash
py src/orchestration/run_pipeline_e2e.py
```

### 🔹 Modo 4: Suite de Fallas Controladas (Demo de Errores)
Ejecuta simulaciones de archivos inexistentes, extensiones inválidas, datasets vacíos y esquemas rotos:
```bash
py tests/test_controlled_failures.py
```

## 5. Estructura del Repositorio
financial-digital-twin/
├── data/
│   ├── raw/                      # Archivos CSV crudos (origen)
│   ├── bronze/                   # Datasets Parquet inmutables + Metadatos
│   │   └── manifest.json         # Control de versiones e idempotencia por Hash SHA-256
│   ├── silver/                   # Datos limpios (dim_clientes, dim_compromisos, fct_transacciones)
│   └── quarantine/               # Registros anómalos (transacciones_cuarentena.parquet)
├── docs/
│   ├── canvas-v0.md              # Documento de diseño arquitectural
│   └── data_profiling_report.md  # Reporte estadístico generado automáticamente
├── logs/
│   └── ingestion_log.csv         # Bitácora histórica estructurada de ingesta
├── src/
│   ├── ingestion/
│   │   ├── fetch_drive_data.py   # Conector con Google Drive / Sheets
│   │   └── pipeline.py           # Pipeline de ingesta con validación de contrato
│   ├── quality/
│   │   └── profile_data.py       # Motor de perfilado de datos y generación de reportes
│   ├── transformations/
│   │   └── transform_silver.py   # Transformación Silver y aislamiento en Cuarentena
│   ├── orchestration/
│   │   └── run_pipeline_e2e.py   # Orquestador del flujo integral de capas
│   └── automation/
│       ├── auto_watcher.py       # Centinela local de archivos en tiempo real
│       └── live_drive_watcher.py # Sincronizador en vivo con Google Drive
├── tests/
│   └── test_controlled_failures.py # Pruebas automatizadas de fallas controladas
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md

## 6. Evidencias de Auditoría
* **Manifest de Ingesta**: data/bronze/manifest.json registra hashes SHA-256, conteo de filas y fechas UTC de procesamiento.
* **Log Consolidado**: logs/ingestion_log.csv audita cada intento de ejecución con estados SUCCESS, WARNING, SKIPPED, REJECTED o FAILED.
* **Reporte de Calidad**: docs/data_profiling_report.md documenta la distribución estadística, nulos y anomalías de los datos.
