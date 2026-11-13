import os
import time
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIGURACION ────────────────────────────────────────────
DATA_PATH = os.getenv("DATA_PATH", r"C:\ruta\a\home-credit-default-risk")
CONN      = os.getenv("SUPABASE_URL")
N_FILAS   = int(os.getenv("N_FILAS", 50_000))   # cambia para cargar mas o menos filas
# ──────────────────────────────────────────────────────────────

if not CONN:
    raise ValueError("Falta la variable de entorno SUPABASE_URL. Copia .env.example a .env y completala.")

engine = create_engine(CONN)

archivos = {
    "application_train":     "application_train.csv",
    "bureau":                "bureau.csv",
    "bureau_balance":        "bureau_balance.csv",
    "previous_application":  "previous_application.csv",
    "credit_card_balance":   "credit_card_balance.csv",
    "pos_cash_balance":      "POS_CASH_balance.csv",
    "installments_payments": "installments_payments.csv",
}

print("=" * 55)
print("  HOME CREDIT -- Carga a Supabase ({} filas por tabla)".format(N_FILAS))
print("=" * 55)

inicio_global = time.time()

for tabla, archivo in archivos.items():
    filepath = os.path.join(DATA_PATH, archivo)

    if not os.path.exists(filepath):
        print("[SKIP] No encontrado: {}".format(archivo))
        continue

    tam_mb = round(os.path.getsize(filepath) / 1024 / 1024, 1)
    print("\n[CARGANDO] {} ({} MB) --> {} filas...".format(tabla, tam_mb, N_FILAS))
    inicio = time.time()

    df = pd.read_csv(filepath, nrows=N_FILAS, low_memory=False)
    df.to_sql(tabla, engine, if_exists="replace", index=False)

    elapsed = round(time.time() - inicio, 1)
    print("[OK] '{}' -- {:,} filas cargadas en {}s".format(tabla, len(df), elapsed))

elapsed_total = round(time.time() - inicio_global, 1)
print("\n" + "=" * 55)
print("CARGA COMPLETA -- Tiempo total: {}s".format(elapsed_total))
print("=" * 55)
