import os
import pandas as pd
import numpy as np
from datetime import datetime

GOLD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "gold", "gold_cliente_mes.parquet"))

def get_financial_summary(authenticated_customer_id: str, periodo: str = None) -> dict:
    if not os.path.exists(GOLD_PATH):
        return {"status": "error", "message": "Capa Gold no encontrada"}
    
    df_gold = pd.read_parquet(GOLD_PATH)
    df_user = df_gold[df_gold["customer_id"] == authenticated_customer_id]
    
    if df_user.empty:
        return {"status": "insufficient_history", "message": "No hay suficiente historial para este usuario en la Capa Gold."}
    
    if periodo and periodo in df_user["periodo"].values:
        row = df_user[df_user["periodo"] == periodo].iloc[0]
    else:
        row = df_user.sort_values("periodo").iloc[-1]
    
    col_deuda = 'pago_deuda_mensual' if 'pago_deuda_mensual' in row.index else 'pagos_deuda'
    val_deuda = float(row.get(col_deuda, 0.0))
    val_ingresos = float(row.get('ingresos_totales', 0.0))
    val_gastos_tot = float(row.get('gastos_totales', 0.0))
    val_gastos_op = float(row.get('gastos_operativos', max(0.0, val_gastos_tot - val_deuda)))
    val_flujo = float(row.get('flujo_neto', 0.0))
    val_ahorro = float(row.get('tasa_ahorro', 0.0)) * 100

    return {
        "status": "success",
        "customer_id": authenticated_customer_id,
        "periodo": str(row.get("periodo")),
        "ingresos_totales": val_ingresos,
        "gastos_operativos": val_gastos_op,
        "pago_deuda": val_deuda,
        "flujo_neto": val_flujo,
        "tasa_ahorro_pct": val_ahorro,
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_financial_goal(authenticated_customer_id: str, goal_id: str = "meta_emergencia") -> dict:
    summary = get_financial_summary(authenticated_customer_id)
    if summary.get("status") != "success":
        return summary

    flujo = summary.get("flujo_neto", 0.0)
    target_amount = 50000.0
    current_saved = max(0.0, flujo * 3)
    remaining = max(0.0, target_amount - current_saved)
    monthly_capacity = max(1000.0, flujo)
    months_needed = int(np.ceil(remaining / monthly_capacity)) if monthly_capacity > 0 else 999

    return {
        "status": "success",
        "goal_id": goal_id,
        "nombre_meta": "Fondo de Emergencia (50,000 MXN)",
        "monto_objetivo": target_amount,
        "saldo_actual": current_saved,
        "monto_faltante": remaining,
        "capacidad_ahorro_mensual": monthly_capacity,
        "plazo_estimado_meses": months_needed
    }

def simulate_goal(authenticated_customer_id: str, pct_gasto_reduccion: float = 0.0, aporte_extra: float = 0.0) -> dict:
    goal_info = get_financial_goal(authenticated_customer_id)
    if goal_info.get("status") != "success":
        return goal_info

    summary = get_financial_summary(authenticated_customer_id)
    gastos_op = summary.get("gastos_operativos", 0.0)
    flujo_actual = summary.get("flujo_neto", 0.0)

    ahorro_adicional = (gastos_op * (pct_gasto_reduccion / 100.0)) + aporte_extra
    nueva_capacidad = flujo_actual + ahorro_adicional

    monto_faltante = goal_info.get("monto_faltante", 0.0)
    nuevo_plazo = int(np.ceil(monto_faltante / nueva_capacidad)) if nueva_capacidad > 0 else 999
    plazo_anterior = goal_info.get("plazo_estimado_meses", 999)
    meses_reducidos = max(0, plazo_anterior - nuevo_plazo)

    return {
        "status": "success",
        "ahorro_adicional_mensual": ahorro_adicional,
        "nueva_capacidad_mensual": nueva_capacidad,
        "nuevo_plazo_meses": nuevo_plazo,
        "meses_reducidos": meses_reducidos,
        "supuestos": f"Reducción hipotética del {pct_gasto_reduccion}% en gastos variables y aportación extra de ${aporte_extra:,.2f} MXN."
    }