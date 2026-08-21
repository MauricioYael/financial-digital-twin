import os
import glob
import pandas as pd

BRONZE_DIR = "data/bronze"
DOCS_DIR = "docs"
REPORT_PATH = os.path.join(DOCS_DIR, "data_profiling_report.md")

os.makedirs(DOCS_DIR, exist_ok=True)

def profile_dataset(file_path: str) -> dict:
    df = pd.read_parquet(file_path)
    file_name = os.path.basename(file_path)
    
    profile = {
        "file_name": file_name,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "null_counts": df.isnull().sum().to_dict(),
        "duplicates": int(df.duplicated(subset=[df.columns[0]]).sum()) if len(df.columns) > 0 else 0,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()}
    }
    
    if "monto" in df.columns:
        numeric_monto = pd.to_numeric(df["monto"], errors="coerce")
        profile["negative_amounts"] = int((numeric_monto < 0).sum())
        profile["null_amounts"] = int(numeric_monto.isnull().sum())
        profile["min_monto"] = float(numeric_monto.min()) if not numeric_monto.dropna().empty else None
        profile["max_monto"] = float(numeric_monto.max()) if not numeric_monto.dropna().empty else None
        profile["mean_monto"] = float(numeric_monto.mean()) if not numeric_monto.dropna().empty else None

    return profile

def generate_markdown_report(profiles: list):
    lines = [
        "# 📋 Reporte de Perfilado de Datos (Data Profiling Report)",
        "",
        "> **Resumen de calidad e integridad de datos ingeridos en la Capa Bronze antes de la transformación a Silver.**",
        "",
        "---",
        ""
    ]
    
    for p in profiles:
        lines.append(f"## 🔹 Dataset: `{p['file_name']}`")
        lines.append(f"* **Total de Registros:** {p['total_rows']}")
        lines.append(f"* **Total de Columnas:** {p['total_columns']}")
        lines.append(f"* **Posibles Duplicados en Clave Primaria:** {p['duplicates']}")
        lines.append("")
        lines.append("### Conteo de Nulos y Tipos de Datos:")
        lines.append("| Columna | Tipo de Dato | Valores Nulos | % Nulidad |")
        lines.append("| :--- | :--- | :--- | :--- |")
        for col in p["columns"]:
            nulls = p["null_counts"].get(col, 0)
            pct = (nulls / p["total_rows"] * 100) if p["total_rows"] > 0 else 0
            lines.append(f"| `{col}` | `{p['dtypes'].get(col)}` | {nulls} | {pct:.1f}% |")
        
        if "negative_amounts" in p:
            lines.append("")
            lines.append("### Hallazgos de Calidad en Montos:")
            lines.append(f"* **Montos Negativos detectados:** {p['negative_amounts']}")
            lines.append(f"* **Montos Inválidos/Nulos:** {p['null_amounts']}")
            lines.append(f"* **Rango Monetario:** Mínimo: `${p['min_monto']:.2f}` | Máximo: `${p['max_monto']:.2f}` | Promedio: `${p['mean_monto']:.2f}`")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ Reporte de perfilado generado exitosamente en: {REPORT_PATH}")

def run_profiling():
    parquet_files = glob.glob(os.path.join(BRONZE_DIR, "*.parquet"))
    if not parquet_files:
        print(f"⚠️ No se encontraron archivos Parquet en {BRONZE_DIR}. Ejecuta primero ingest_bronze.py.")
        return

    profiles = [profile_dataset(f) for f in parquet_files]
    generate_markdown_report(profiles)

if __name__ == "__main__":
    run_profiling()
