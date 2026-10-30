import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_synthetic_dataset_24m(output_dir="data/raw"):
    """
    Genera un conjunto de datos sintéticos de 24 meses para 100 clientes,
    incluyendo compromisos fijos y eventos extraordinarios (gastos imprevistos / ingresos cero).
    """
    os.makedirs(output_dir, exist_ok=True)
    np.random.seed(42)

    n_clients = 100
    n_months = 24
    start_date = datetime(2024, 1, 1)

    # 1. GENERACIÓN DE CLIENTES (100 perfiles)
    customer_ids = [f"C{str(i).zfill(4)}" for i in range(1, n_clients + 1)]
    base_incomes = np.random.choice([15000, 25000, 35000, 50000, 75000], size=n_clients, p=[0.2, 0.3, 0.3, 0.15, 0.05])
    
    df_clientes = pd.DataFrame({
        "customer_id": customer_ids,
        "nombre": [f"Cliente_{i}" for i in range(1, n_clients + 1)],
        "ingreso_base": base_incomes,
        "estatus": "Activo"
    })
    df_clientes.to_csv(os.path.join(output_dir, "clientes.csv"), index=False)

    # 2. GENERACIÓN DE COMPROMISOS FIJOS / CRÉDITOS
    compromisos = []
    for cid, inc in zip(customer_ids, base_incomes):
        if np.random.rand() > 0.3:  # 70% de clientes tienen créditos/compromisos fijos
            pago_mensual = round(inc * np.random.uniform(0.10, 0.35), 2)
            saldo = round(pago_mensual * np.random.randint(6, 36), 2)
            compromisos.append({
                "customer_id": cid,
                "concepto": np.random.choice(["Crédito Hipotecario", "Préstamo Personal", "Crédito Automotriz"]),
                "pago_mensual": pago_mensual,
                "saldo_pendiente": saldo
            })
    df_compromisos = pd.DataFrame(compromisos)
    df_compromisos.to_csv(os.path.join(output_dir, "compromisos_fijos.csv"), index=False)

    # 3. GENERACIÓN DE TRANSACCIONES (24 Meses)
    transactions = []
    tx_counter = 1

    for m in range(n_months):
        current_month_start = start_date + timedelta(days=m * 30)
        
        for cid, inc in zip(customer_ids, base_incomes):
            # A. Ingesta de Ingreso Principal
            # Caso Límite: 2% de probabilidad de ingreso en cero en un mes específico
            is_zero_income = np.random.rand() < 0.02
            income_amount = 0.0 if is_zero_income else round(inc * np.random.uniform(0.95, 1.05), 2)
            
            if income_amount > 0:
                transactions.append({
                    "transaction_id": f"TX_{str(tx_counter).zfill(6)}",
                    "customer_id": cid,
                    "fecha": (current_month_start + timedelta(days=int(np.random.randint(1, 5)))).strftime("%Y-%m-%d"),
                    "tipo": "Ingreso",
                    "categoria": "Nómina",
                    "monto": income_amount,
                    "estatus": "Completada"
                })
                tx_counter += 1

            # B. Gastos Operativos Ordinarios (Supermercado, Servicios, Servicios)
            n_expenses = np.random.randint(4, 10)
            avg_expense = (inc * 0.50) / n_expenses
            
            for _ in range(n_expenses):
                transactions.append({
                    "transaction_id": f"TX_{str(tx_counter).zfill(6)}",
                    "customer_id": cid,
                    "fecha": (current_month_start + timedelta(days=int(np.random.randint(1, 28)))).strftime("%Y-%m-%d"),
                    "tipo": "Gasto",
                    "categoria": np.random.choice(["Supermercado", "Servicios", "Entretenimiento", "Restaurantes"]),
                    "monto": round(max(10.0, np.random.normal(avg_expense, avg_expense * 0.2)), 2),
                    "estatus": "Completada"
                })
                tx_counter += 1

            # C. Caso Límite: Gastos Extraordinarios (Médicos / Imprevistos)
            if np.random.rand() < 0.05:  # 5% de probabilidad al mes
                transactions.append({
                    "transaction_id": f"TX_{str(tx_counter).zfill(6)}",
                    "customer_id": cid,
                    "fecha": (current_month_start + timedelta(days=int(np.random.randint(10, 25)))).strftime("%Y-%m-%d"),
                    "tipo": "Gasto",
                    "categoria": "Gasto Extraordinario",
                    "monto": round(inc * np.random.uniform(0.40, 0.80), 2),
                    "estatus": "Completada"
                })
                tx_counter += 1

            # D. Pagos de Deuda Registrados como Transacción
            client_comp = [c for c in compromisos if c["customer_id"] == cid]
            if client_comp:
                transactions.append({
                    "transaction_id": f"TX_{str(tx_counter).zfill(6)}",
                    "customer_id": cid,
                    "fecha": (current_month_start + timedelta(days=15)).strftime("%Y-%m-%d"),
                    "tipo": "Gasto",
                    "categoria": "Pago de Crédito",
                    "monto": client_comp[0]["pago_mensual"],
                    "estatus": "Completada"
                })
                tx_counter += 1

    df_tx = pd.DataFrame(transactions)
    df_tx.to_csv(os.path.join(output_dir, "transacciones.csv"), index=False)

    print(f"✅ Generación sintética de 24 meses completada exitosamente en '{output_dir}'.")
    print(f"   - Clientes: {len(df_clientes)}")
    print(f"   - Transacciones totales: {len(df_tx)}")
    print(f"   - Compromisos fijos: {len(df_compromisos)}")

if __name__ == "__main__":
    generate_synthetic_dataset_24m()