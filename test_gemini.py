import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

# Cargar variables de entorno
load_dotenv(override=True)

# Obtener API Key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("No se encontró GEMINI_API_KEY en .env")

print("API Key encontrada:", bool(api_key))
print("Prefijo de la clave:", api_key[:3])

# Crear cliente Gemini
client = genai.Client(api_key=api_key)

# Primero el modelo principal, después respaldos
MODELOS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash-lite",
]

def generar(prompt: str, max_intentos: int = 3) -> tuple[str, str]:
    """Devuelve (texto, modelo_usado). Reintenta en errores 5xx y pasa al siguiente modelo."""
    for modelo in MODELOS:
        for intento in range(1, max_intentos + 1):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                )
                return response.text, modelo
            except errors.ServerError as e:
                espera = 2 ** intento  # 2, 4, 8 segundos
                print(f"[{modelo}] intento {intento}/{max_intentos} falló ({e.code}). "
                      f"Reintentando en {espera}s...")
                time.sleep(espera)
        print(f"[{modelo}] sin respuesta, probando el siguiente modelo...")
    raise RuntimeError("Ningún modelo respondió. Intenta de nuevo en unos minutos.")

texto, modelo = generar("Responde únicamente: conexión exitosa")

print(f"\nRespuesta de Gemini ({modelo}):")
print(texto)