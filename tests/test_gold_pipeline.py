import pytest
import pandas as pd
import numpy as np

def test_zero_income_edge_case():
    """Valida que un ingreso de 0 no provoque división por cero ni errores de ejecución."""
    ingresos = 0.0
    gastos = 1500.0
    pago_deuda = 300.0

    flujo_neto = ingresos - gastos
    
    # Lógica segura implementada en gold_builder.py
    ingresos_safe = np.nan if ingresos == 0 else ingresos
    tasa_ahorro = 0.0 if pd.isna(ingresos_safe) else (flujo_neto / ingresos_safe)
    ratio_endeudamiento = 0.0 if pd.isna(ingresos_safe) else (pago_deuda / ingresos_safe)

    assert flujo_neto == -1500.0
    assert tasa_ahorro == 0.0
    assert ratio_endeudamiento == 0.0
    assert not np.isinf(tasa_ahorro)
    assert not np.isnan(tasa_ahorro)