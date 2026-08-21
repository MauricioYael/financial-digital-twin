import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

RAW_DIR = "data/raw"
os.makedirs(RAW_DIR, exist_ok=True)

SOURCES = {
    "clientes.csv": os.getenv("SHEET_ID_CLIENTES", "1XTwn9NPJ9EwU3VsU0_bnwbe2WFyC1Fbfhqmd9UD9YSs"),
    "compromisos_fijos.csv": os.getenv("SHEET_ID_COMPROMISOS", "1G923Te8qYunq7feq8iHN4EyLYKehzFproXJSWrlduVQ"),
    "transacciones.csv": os.getenv("SHEET_ID_TRANSACCIONES", "1YG_4mTcroFPNSx8Tws0n_BbzD1Lb132udI74JP-0RDE")
}

def download_sheet(sheet_id: str, output_path: str):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    try:
        print(f"Descargando: {output_path} desde Drive...")
        df = pd.read_csv(url)
        df.to_csv(output_path, index=False)
        print(f"✓ Guardado: {output_path} ({len(df)} filas)")
    except Exception as e:
        print(f"❌ Error al descargar {output_path}: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO EXTRACCIÓN DESDE GOOGLE DRIVE")
    for filename, sheet_id in SOURCES.items():
        download_sheet(sheet_id, os.path.join(RAW_DIR, filename))
    print("✅ EXTRACCIÓN COMPLETADA")