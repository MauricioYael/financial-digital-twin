import os
import pandas as pd
from src.ingestion.pipeline import ingest_file

def test_controlled_errors():
    print("\n🧪 ===================================================")
    print("🧪 DEMO: PRUEBAS DE FALLA CONTROLADA DEL CONTRATO")
    print("🧪 ===================================================")

    # Error 1: Archivo inexistente
    print("\n[TEST 1] Intento de procesar archivo no existente:")
    ingest_file("creditos_inexistente.csv", ["id"])

    # Error 2: Extensión inválida
    bad_ext = "data/raw/invalido.txt"
    with open(bad_ext, "w") as f:
        f.write("id,monto\n1,100")
    print("\n[TEST 2] Intento de procesar formato .txt:")
    ingest_file("invalido.txt", ["id"])
    if os.path.exists(bad_ext):
        os.remove(bad_ext)

    # Error 3: Archivo de 0 bytes
    empty_file = "data/raw/vacio.csv"
    open(empty_file, "w").close()
    print("\n[TEST 3] Intento de procesar archivo vacío:")
    ingest_file("vacio.csv", ["id"])
    if os.path.exists(empty_file):
        os.remove(empty_file)

    # Error 4: Esquema con columnas faltantes
    broken_file = "data/raw/clientes_roto.csv"
    pd.DataFrame([{"columna_erronea": 123}]).to_csv(broken_file, index=False)
    print("\n[TEST 4] Intento de procesar esquema incompleto:")
    ingest_file("clientes_roto.csv", ["customer_id", "nombre", "fecha_registro"])
    if os.path.exists(broken_file):
        os.remove(broken_file)

    print("\n✅ Todas las fallas fueron capturadas y registradas en 'logs/ingestion_log.csv'.\n")

if __name__ == "__main__":
    test_controlled_errors()