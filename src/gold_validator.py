import os
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GOLD_PATH = os.path.join(BASE_DIR, "data", "gold", "gold_cliente_mes.parquet")

def validate_gold():
    print("🔍 Ejecutando Suit de Calidad para la Capa Gold...\n")
    if not os.path.exists(GOLD_PATH):
        print("❌ Error: No existe el archivo gold_cliente_mes.parquet")
        return

    df = pd.read_parquet(GOLD_PATH)
    errores = 0

    # 1. Integridad: Unicidad de (customer_id, periodo)
    duplicados = df.duplicated(subset=['customer_id', 'periodo']).sum()
    if duplicados == 0:
        print("✔ [Integridad]: Clave primaria (customer_id + periodo) es única.")
    else:
        print(f"✖ [Integridad]: Se encontraron {duplicados} llaves duplicadas.")
        errores += 1

    # 2. Rangos: Tasa de ahorro y ratios entre 0 y 1
    tasa_out = df[(df['tasa_ahorro'] < 0) | (df['tasa_ahorro'] > 1)]
    ratio_fijo_out = df[(df['ratio_fijo'] < 0) | (df['ratio_fijo'] > 1)]
    
    if len(tasa_out) == 0 and len(ratio_fijo_out) == 0:
        print("✔ [Rangos]: Todos los ratios (tasa_ahorro, ratio_fijo) están en el rango válido [0.0, 1.0].")
    else:
        print(f"✖ [Rangos]: Se detectaron {len(tasa_out) + len(ratio_fijo_out)} registros fuera de rango.")
        errores += 1

    # 3. Consistencia Aritmética: flujo_neto == ingresos_totales - gastos_totales
    diff = (df['flujo_neto'] - (df['ingresos_totales'] - df['gastos_totales'])).abs()
    inconsistencias = (diff > 0.01).sum()
    if inconsistencias == 0:
        print("✔ [Consistencia]: El cálculo de flujo_neto cuadra numéricamente con ingresos y gastos.")
    else:
        print(f"✖ [Consistencia]: Se hallaron {inconsistencias} diferencias aritméticas en flujo_neto.")
        errores += 1

    # Resumen
    print("\n" + "="*40)
    if errores == 0:
        print("🎉 CAPA GOLD APROBADA: Todos los controles pasaron correctamente.")
    else:
        print(f"⚠️ CAPA GOLD RECHAZADA: {errores} validaciones fallaron.")
    print("="*40)

if __name__ == "__main__":
    validate_gold()