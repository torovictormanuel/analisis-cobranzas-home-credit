"""
Exporta las 5 tablas mart desde Supabase a CSV para cargar en Qlik Sense Cloud.
Los archivos quedan en la carpeta qlik_data/ dentro del proyecto.
"""
import os
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CONN = os.getenv("SUPABASE_URL")
if not CONN:
    raise ValueError("Falta la variable de entorno SUPABASE_URL.")

engine = create_engine(CONN)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "qlik_data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

tablas = {
    "dim_cliente":  "SELECT * FROM dim_cliente",
    "dim_producto": "SELECT * FROM dim_producto",
    "dim_tiempo":   "SELECT * FROM dim_tiempo",
    "fact_pagos":   "SELECT * FROM fact_pagos",
    "fact_aging":   "SELECT * FROM fact_aging",
}

print("=" * 55)
print("  EXPORTANDO TABLAS MART -> CSV para Qlik Sense")
print("=" * 55)

for nombre, sql in tablas.items():
    print(f"\n[EXPORTANDO] {nombre}...")
    with engine.connect() as c:
        df = pd.read_sql(text(sql), c)

    ruta = os.path.join(OUTPUT_DIR, f"{nombre}.csv")
    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    tam_kb = round(os.path.getsize(ruta) / 1024, 1)
    print(f"  OK -> {nombre}.csv  |  {len(df):,} filas  |  {len(df.columns)} cols  |  {tam_kb} KB")

print("\n" + "=" * 55)
print(f"  Archivos guardados en: {OUTPUT_DIR}")
print("=" * 55)
