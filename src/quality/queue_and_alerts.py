import os
import sys
import pandas as pd
import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
QUEUE_LOG = os.path.join(PROJECT_ROOT, "logs", "traffic_alerts.log")
os.makedirs(os.path.join(PROJECT_ROOT, "logs"), exist_ok=True)

# Umbrales operativos
HIGH_TRAFFIC_THRESHOLD_PER_HOUR = 50   # Alerta de alta concurrencia
LOW_TRAFFIC_THRESHOLD_PER_DAY = 5      # Alerta de caída inusual de actividad

def inspect_traffic_and_queue(df: pd.DataFrame) -> dict:
    """
    Analiza la distribución horaria de las transacciones para evitar saturación de procesamiento.
    """
    if df.empty or "fecha" not in df.columns:
        return {"status": "EMPTY"}

    df["dt"] = pd.to_datetime(df["fecha"])
    df["hour"] = df["dt"].dt.hour
    df["date"] = df["dt"].dt.date

    # Conteo por hora
    hourly_counts = df.groupby(["date", "hour"]).size().reset_index(name="tx_count")
    total_tx = len(df)

    alerts = []
    
    # 1. Alerta por exceso de volumen por hora (Día pesado / Hora pico)
    peak_hours = hourly_counts[hourly_counts["tx_count"] >= HIGH_TRAFFIC_THRESHOLD_PER_HOUR]
    for _, row in peak_hours.iterrows():
        msg = f"[ALERTA TRÁFICO ALTO] {row['date']} Hora {row['hour']}:00 hrs con {row['tx_count']} txs. Requiere micro-batching."
        alerts.append(msg)
        print(f"⚠️  {msg}")

    # 2. Alerta por bajo volumen (Día lento o posible falla de recepción)
    if total_tx < LOW_TRAFFIC_THRESHOLD_PER_DAY:
        msg = f"[ALERTA TRÁFICO BAJO] Volumen diario inusualmente bajo ({total_tx} txs en el lote)."
        alerts.append(msg)
        print(f"ℹ️  {msg}")

    # Guardar en log de alertas
    with open(QUEUE_LOG, "a", encoding="utf-8") as f:
        for alert in alerts:
            f.write(f"{datetime.datetime.now().isoformat()} - {alert}\n")

    return {
        "total_records": total_tx,
        "hourly_distribution": hourly_counts.to_dict(orient="records"),
        "alerts": alerts
    }