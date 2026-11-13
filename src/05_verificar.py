"""
Verifica que las 7 tablas raw y las 5 tablas mart existen en Supabase
e imprime filas y columnas de cada una.
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

CONN = os.getenv("SUPABASE_URL")
if not CONN:
    raise ValueError("Falta la variable de entorno SUPABASE_URL.")

engine = create_engine(CONN)

tablas_raw = [
    "application_train",
    "bureau",
    "bureau_balance",
    "previous_application",
    "credit_card_balance",
    "pos_cash_balance",
    "installments_payments",
]

tablas_mart = [
    "dim_cliente",
    "dim_producto",
    "dim_tiempo",
    "fact_pagos",
    "fact_aging",
]

def verificar(tablas, titulo):
    print("\n" + "=" * 55)
    print(f"  {titulo}")
    print("=" * 55)
    print("{:<30} {:>10} {:>8}".format("TABLA", "FILAS", "COLS"))
    print("-" * 52)
    with engine.connect() as c:
        for t in tablas:
            try:
                filas = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
                cols  = c.execute(text(
                    f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name='{t}'"
                )).scalar()
                print("{:<30} {:>10,} {:>8}".format(t, filas, cols))
            except Exception as e:
                print("{:<30} ERROR: {}".format(t, e))
    print("-" * 52)

verificar(tablas_raw, "RAW LAYER")
verificar(tablas_mart, "MART LAYER (Star Schema)")
print("\nVerificacion completa.")
