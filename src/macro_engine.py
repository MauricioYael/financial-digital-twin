import pandas as pd
import numpy as np

def calculate_macro_projections(df_gold, inflation_annual=0.045, usd_mxn=18.50):
    """
    Calcula proyecciones inerciales a 3 y 6 meses ajustadas por inflación y tipo de cambio USD/MXN.
    Compatible con los nombres de columna de la capa Gold (gold_cliente_mes.parquet).
    """
    if df_gold.empty:
        return pd.DataFrame()
    
    # Tasa de inflación mensual equivalente a partir de la anual
    monthly_inflation = (1 + inflation_annual) ** (1/12) - 1
    
    projections = []
    for idx, row in df_gold.iterrows():
        base_flow = row.get('flujo_neto', 0.0)
        
        # Lectura flexible para soportar tanto 'pagos_deuda' como 'pago_deuda_mensual'
        p_deuda = row.get('pagos_deuda', row.get('pago_deuda_mensual', 0.0))
        
        # Gastos operativos (si no existe como columna directa, se deduce restando la deuda a gastos totales)
        g_tot = row.get('gastos_totales', 0.0)
        g_op = row.get('gastos_operativos', max(0.0, g_tot - p_deuda))
        
        # Proyecciones ajustadas por la inflación acumulada a 3 y 6 meses
        inf_factor_3m = (1 - monthly_inflation * 3)
        flow_3m = (base_flow * 3) * inf_factor_3m
        
        inf_factor_6m = (1 - monthly_inflation * 6)
        flow_6m = (base_flow * 6) * inf_factor_6m
        
        projections.append({
            "customer_id": str(row.get('customer_id', '')),
            "periodo_base": str(row.get('periodo', '')),
            "flujo_neto_mensual": round(float(base_flow), 2),
            "pagos_deuda": round(float(p_deuda), 2),
            "gastos_operativos": round(float(g_op), 2),
            "proyeccion_3m_mxn": round(float(flow_3m), 2),
            "proyeccion_6m_mxn": round(float(flow_6m), 2),
            "proyeccion_3m_usd": round(float(flow_3m / usd_mxn), 2),
            "proyeccion_6m_usd": round(float(flow_6m / usd_mxn), 2),
            "impacto_inflacion_3m": round(float((base_flow * 3) - flow_3m), 2)
        })
        
    return pd.DataFrame(projections)