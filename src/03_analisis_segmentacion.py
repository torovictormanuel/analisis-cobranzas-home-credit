"""
Bloque 3: Segmentacion de riesgo por variables demograficas
Bloque 4: Comportamiento de pago y recupero
Bloque 5: Clientes criticos e historial en buro

14 queries en total sobre las tablas raw en Supabase.
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

def run(titulo, sql):
    print("\n" + "=" * 65)
    print("  " + titulo)
    print("=" * 65)
    with engine.connect() as c:
        df = pd.read_sql(text(sql), c)
        print(df.to_string(index=False))
    return df

# ─────────────────────────────────────────────────────────────
# BLOQUE 3 — SEGMENTACION DE RIESGO
# ─────────────────────────────────────────────────────────────

run("P7 | Default por Tipo de Empleo", """
    SELECT
        "NAME_INCOME_TYPE"                                                     AS tipo_ingreso,
        COUNT(*)                                                               AS clientes,
        SUM("TARGET")                                                          AS defaults,
        ROUND(AVG(CASE WHEN "TARGET"=1 THEN 100.0 ELSE 0 END)::numeric, 2)   AS tasa_default_pct,
        ROUND(AVG("AMT_INCOME_TOTAL")::numeric, 0)                            AS ingreso_promedio
    FROM application_train
    GROUP BY "NAME_INCOME_TYPE"
    HAVING COUNT(*) > 100
    ORDER BY tasa_default_pct DESC
""")

run("P8 | Default por Nivel Educativo", """
    SELECT
        "NAME_EDUCATION_TYPE"                                                  AS educacion,
        COUNT(*)                                                               AS clientes,
        ROUND(AVG(CASE WHEN "TARGET"=1 THEN 100.0 ELSE 0 END)::numeric, 2)   AS tasa_default_pct
    FROM application_train
    GROUP BY "NAME_EDUCATION_TYPE"
    ORDER BY tasa_default_pct DESC
""")

run("P9 | Default por Carga Financiera (cuota / ingreso)", """
    SELECT
        CASE
            WHEN "AMT_ANNUITY"/"AMT_INCOME_TOTAL" < 0.10 THEN '1. Menos del 10pct'
            WHEN "AMT_ANNUITY"/"AMT_INCOME_TOTAL" < 0.20 THEN '2. 10pct a 20pct'
            WHEN "AMT_ANNUITY"/"AMT_INCOME_TOTAL" < 0.30 THEN '3. 20pct a 30pct'
            WHEN "AMT_ANNUITY"/"AMT_INCOME_TOTAL" < 0.50 THEN '4. 30pct a 50pct'
            ELSE                                               '5. Mas del 50pct'
        END                                                                    AS carga_financiera,
        COUNT(*)                                                               AS clientes,
        ROUND(AVG(CASE WHEN "TARGET"=1 THEN 100.0 ELSE 0 END)::numeric, 2)   AS tasa_default_pct
    FROM application_train
    WHERE "AMT_ANNUITY" IS NOT NULL AND "AMT_INCOME_TOTAL" > 0
    GROUP BY 1
    ORDER BY 1
""")

run("P10 | Default por Rango de Edad", """
    SELECT
        CASE
            WHEN "DAYS_BIRTH"/-365 BETWEEN 20 AND 30 THEN '1. 20-30 anos'
            WHEN "DAYS_BIRTH"/-365 BETWEEN 31 AND 40 THEN '2. 31-40 anos'
            WHEN "DAYS_BIRTH"/-365 BETWEEN 41 AND 50 THEN '3. 41-50 anos'
            WHEN "DAYS_BIRTH"/-365 BETWEEN 51 AND 60 THEN '4. 51-60 anos'
            ELSE                                           '5. Mas de 60 anos'
        END                                                                    AS rango_edad,
        COUNT(*)                                                               AS clientes,
        ROUND(AVG(CASE WHEN "TARGET"=1 THEN 100.0 ELSE 0 END)::numeric, 2)   AS tasa_default_pct
    FROM application_train
    GROUP BY 1
    ORDER BY 1
""")

# ─────────────────────────────────────────────────────────────
# BLOQUE 4 — COMPORTAMIENTO DE PAGO
# ─────────────────────────────────────────────────────────────

run("P11 | Puntualidad de Pagos", """
    SELECT
        COUNT(*)                                                               AS total_cuotas,
        COUNT("DAYS_ENTRY_PAYMENT")                                            AS cuotas_pagadas,
        COUNT(CASE WHEN "DAYS_ENTRY_PAYMENT" IS NULL THEN 1 END)              AS sin_pagar,
        COUNT(CASE WHEN "DAYS_ENTRY_PAYMENT" > "DAYS_INSTALMENT" THEN 1 END)  AS pagadas_tarde,
        ROUND(
            COUNT(CASE WHEN "DAYS_ENTRY_PAYMENT" > "DAYS_INSTALMENT" THEN 1 END)*100.0
            / NULLIF(COUNT("DAYS_ENTRY_PAYMENT"),0), 2)                       AS pct_tardias,
        ROUND(AVG(
            CASE WHEN "DAYS_ENTRY_PAYMENT" > "DAYS_INSTALMENT"
                 THEN "DAYS_ENTRY_PAYMENT" - "DAYS_INSTALMENT" END
        )::numeric, 1)                                                         AS atraso_promedio_dias
    FROM installments_payments
""")

run("P12 | Tasa de Recupero y DSO", """
    SELECT
        ROUND(SUM("AMT_INSTALMENT")::numeric, 0)                              AS total_facturado,
        ROUND(SUM(COALESCE("AMT_PAYMENT", 0))::numeric, 0)                   AS total_cobrado,
        ROUND((SUM("AMT_INSTALMENT")-SUM(COALESCE("AMT_PAYMENT",0)))::numeric,0) AS saldo_pendiente,
        ROUND((SUM(COALESCE("AMT_PAYMENT",0))*100.0
              / NULLIF(SUM("AMT_INSTALMENT"),0))::numeric, 2)                 AS tasa_recupero_pct,
        ROUND(
            ((SUM("AMT_INSTALMENT") - SUM(COALESCE("AMT_PAYMENT",0)))
            / NULLIF(SUM("AMT_INSTALMENT"),0) * 30)::numeric
        , 1)                                                                   AS dso_dias
    FROM installments_payments
""")

# ─────────────────────────────────────────────────────────────
# BLOQUE 5 — CLIENTES CRITICOS
# ─────────────────────────────────────────────────────────────

run("P13 | Top 20 Clientes con Mayor Mora", """
    SELECT
        a."SK_ID_CURR"                        AS cliente_id,
        a."NAME_CONTRACT_TYPE"                AS producto,
        a."AMT_CREDIT"                        AS monto_credito,
        a."NAME_INCOME_TYPE"                  AS tipo_ingreso,
        ROUND(a."DAYS_BIRTH"/-365.0, 0)       AS edad,
        MAX(p."SK_DPD")                       AS max_dias_mora,
        a."TARGET"                            AS defaulteo
    FROM application_train a
    JOIN pos_cash_balance p ON a."SK_ID_CURR" = p."SK_ID_CURR"
    WHERE p."SK_DPD" > 0
    GROUP BY a."SK_ID_CURR", a."NAME_CONTRACT_TYPE", a."AMT_CREDIT",
             a."NAME_INCOME_TYPE", a."DAYS_BIRTH", a."TARGET"
    ORDER BY max_dias_mora DESC
    LIMIT 20
""")

run("P14 | Historial en Buro vs Default Actual", """
    SELECT
        CASE
            WHEN b."CREDIT_DAY_OVERDUE" = 0  THEN '1. Sin mora en buro'
            WHEN b."CREDIT_DAY_OVERDUE" < 30 THEN '2. Mora leve (menos 30d)'
            WHEN b."CREDIT_DAY_OVERDUE" < 90 THEN '3. Mora moderada (30-90d)'
            ELSE                                  '4. Mora grave (90+ dias)'
        END                                                                    AS historial_buro,
        COUNT(DISTINCT a."SK_ID_CURR")                                         AS clientes,
        ROUND(AVG(CASE WHEN a."TARGET"=1 THEN 100.0 ELSE 0 END)::numeric, 2) AS tasa_default_pct
    FROM application_train a
    JOIN bureau b ON a."SK_ID_CURR" = b."SK_ID_CURR"
    GROUP BY 1
    ORDER BY tasa_default_pct DESC
""")

print("\n" + "=" * 65)
print("  ANALISIS COMPLETO TERMINADO")
print("=" * 65)
