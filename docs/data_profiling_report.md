# 📋 Reporte de Perfilado de Datos (Data Profiling Report)

> **Resumen de calidad e integridad de datos ingeridos en la Capa Bronze antes de la transformación a Silver.**

---

## 🔹 Dataset: `clientes.parquet`
* **Total de Registros:** 5
* **Total de Columnas:** 10
* **Posibles Duplicados en Clave Primaria:** 0

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `customer_id` | `str` | 0 | 0.0% |
| `nombre` | `str` | 0 | 0.0% |
| `edad` | `int64` | 0 | 0.0% |
| `ocupacion` | `str` | 0 | 0.0% |
| `ingreso_mensual_base` | `int64` | 0 | 0.0% |
| `saldo_inicial_cuenta` | `int64` | 0 | 0.0% |
| `fecha_alta` | `str` | 0 | 0.0% |
| `_ingested_at` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_sha256_hash` | `str` | 0 | 0.0% |

---

## 🔹 Dataset: `clientes_dummy.parquet`
* **Total de Registros:** 1
* **Total de Columnas:** 10
* **Posibles Duplicados en Clave Primaria:** 0

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `customer_id` | `str` | 0 | 0.0% |
| `nombre` | `str` | 0 | 0.0% |
| `edad` | `int64` | 0 | 0.0% |
| `ocupacion` | `str` | 0 | 0.0% |
| `ingreso_mensual_base` | `float64` | 0 | 0.0% |
| `saldo_inicial_cuenta` | `float64` | 0 | 0.0% |
| `fecha_alta` | `str` | 0 | 0.0% |
| `_ingested_at` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_sha256_hash` | `str` | 0 | 0.0% |

---

## 🔹 Dataset: `compromisos_fijos.parquet`
* **Total de Registros:** 12
* **Total de Columnas:** 10
* **Posibles Duplicados en Clave Primaria:** 0

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `compromiso_id` | `str` | 0 | 0.0% |
| `customer_id` | `str` | 0 | 0.0% |
| `concepto` | `str` | 0 | 0.0% |
| `tipo_compromiso` | `str` | 0 | 0.0% |
| `monto_mensual` | `int64` | 0 | 0.0% |
| `dia_pago_mes` | `int64` | 0 | 0.0% |
| `estado` | `str` | 0 | 0.0% |
| `_ingested_at` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_sha256_hash` | `str` | 0 | 0.0% |

---

## 🔹 Dataset: `compromisos_fijos_dummy.parquet`
* **Total de Registros:** 1
* **Total de Columnas:** 10
* **Posibles Duplicados en Clave Primaria:** 0

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `compromiso_id` | `str` | 0 | 0.0% |
| `customer_id` | `str` | 0 | 0.0% |
| `concepto` | `str` | 0 | 0.0% |
| `tipo_compromiso` | `str` | 0 | 0.0% |
| `monto_mensual` | `float64` | 0 | 0.0% |
| `dia_pago_mes` | `int64` | 0 | 0.0% |
| `estado` | `str` | 0 | 0.0% |
| `_ingested_at` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_sha256_hash` | `str` | 0 | 0.0% |

---

## 🔹 Dataset: `transacciones.parquet`
* **Total de Registros:** 50
* **Total de Columnas:** 11
* **Posibles Duplicados en Clave Primaria:** 2

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `transaction_id` | `str` | 0 | 0.0% |
| `customer_id` | `str` | 0 | 0.0% |
| `fecha` | `str` | 0 | 0.0% |
| `tipo_transaccion` | `str` | 0 | 0.0% |
| `categoria` | `str` | 0 | 0.0% |
| `monto` | `float64` | 1 | 2.0% |
| `canal` | `str` | 0 | 0.0% |
| `estatus` | `str` | 0 | 0.0% |
| `_ingestion_timestamp` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_raw_sha256` | `str` | 0 | 0.0% |

### Hallazgos de Calidad en Montos:
* **Montos Negativos detectados:** 1
* **Montos Inválidos/Nulos:** 1
* **Rango Monetario:** Mínimo: `$-350.00` | Máximo: `$21000.00` | Promedio: `$6517.14`

---

## 🔹 Dataset: `transacciones_dummy.parquet`
* **Total de Registros:** 3
* **Total de Columnas:** 11
* **Posibles Duplicados en Clave Primaria:** 0

### Conteo de Nulos y Tipos de Datos:
| Columna | Tipo de Dato | Valores Nulos | % Nulidad |
| :--- | :--- | :--- | :--- |
| `transaction_id` | `str` | 0 | 0.0% |
| `customer_id` | `str` | 0 | 0.0% |
| `fecha` | `str` | 0 | 0.0% |
| `tipo_transaccion` | `str` | 0 | 0.0% |
| `categoria` | `str` | 0 | 0.0% |
| `monto` | `float64` | 0 | 0.0% |
| `canal` | `str` | 0 | 0.0% |
| `estatus` | `str` | 0 | 0.0% |
| `_ingested_at` | `str` | 0 | 0.0% |
| `_source_file` | `str` | 0 | 0.0% |
| `_sha256_hash` | `str` | 0 | 0.0% |

### Hallazgos de Calidad en Montos:
* **Montos Negativos detectados:** 0
* **Montos Inválidos/Nulos:** 0
* **Rango Monetario:** Mínimo: `$145.50` | Máximo: `$2850.00` | Promedio: `$1221.84`

---
