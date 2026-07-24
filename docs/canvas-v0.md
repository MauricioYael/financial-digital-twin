## 1. Problema
La banca tradicional se limita a presentar reportes transaccionales e históricos (saldos y gastos pasados) sin ofrecer capacidad predictiva para planificar decisiones financieras clave (compras, ahorro, hipotecas)[cite: 1].

## 2. Usuario
Personas que buscan previsibilidad financiera (jóvenes, familias, planificadores de retiro) e instituciones bancarias interesadas en reducir cartera vencida mediante evaluación predictiva[cite: 1].

## 3. Datos
* Fuentes: APIS Open Banking (Plaid Sandbox / Open Banking México) y cargas de datos transaccionales (CSV, JSON)[cite: 1].
* Trazabilidad: Almacenamiento directo en capa cruda (`data/raw`) para auditoría e inmutabilidad.

## 4. MVP (Alcance v0)
* Ingesta de datos crudos con logs de validación.
* Pipeline ETL de limpieza (duplicados, nulos, categorización XGBoost)[cite: 1].
* Proyección a 12 meses (Prophet/LightGBM) y simulación Monte Carlo (1,000 escenarios)[cite: 1].
* Dashboard ejecutivo e interfaz de chat asistida por IA local (Ollama)[cite: 1].

## 5. KPIs de Valor
* **Negocio:** Margen de ahorro proyectado vs. real, tasa de precisión en categorización (>90%).
* **Técnicos:** Latencia de simulación Monte Carlo (< 2 segundos), integridad auditada de datos crudos.

## 6. Riesgos
* Formatos no estandarizados en fuentes bancarias externas.
* Requerimientos de cómputo local para la ejecución del motor LLM (Ollama).
