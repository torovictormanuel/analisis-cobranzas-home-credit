import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

CONN = os.getenv("SUPABASE_URL")
if not CONN:
    raise ValueError("Falta la variable de entorno SUPABASE_URL. Copia .env.example a .env y completala.")

engine = create_engine(CONN)

def ejecutar(nombre, sql):
    print(f"\n[CREANDO] {nombre}...")
    with engine.connect() as c:
        c.execute(text("COMMIT"))
        c.execute(text(sql))
        c.execute(text("COMMIT"))
    print(f"  OK -> {nombre} creada")

# ─────────────────────────────────────────────────────────────
# DIMENSIONES
# ─────────────────────────────────────────────────────────────

ejecutar("dim_cliente", """
    DROP TABLE IF EXISTS dim_cliente;
    CREATE TABLE dim_cliente AS
    SELECT DISTINCT
        "SK_ID_CURR"                                                    AS cliente_key,
        "CODE_GENDER"                                                   AS genero,
        "NAME_EDUCATION_TYPE"                                           AS nivel_educativo,
        "NAME_INCOME_TYPE"                                              AS tipo_ingreso,
        ROUND(ABS("DAYS_BIRTH") / 365.0)                               AS edad,
        CASE
            WHEN ABS("DAYS_BIRTH")/365 BETWEEN 20 AND 30 THEN '20-30 anos'
            WHEN ABS("DAYS_BIRTH")/365 BETWEEN 31 AND 40 THEN '31-40 anos'
            WHEN ABS("DAYS_BIRTH")/365 BETWEEN 41 AND 50 THEN '41-50 anos'
            WHEN ABS("DAYS_BIRTH")/365 BETWEEN 51 AND 60 THEN '51-60 anos'
            ELSE '60+ anos'
        END                                                             AS rango_edad,
        ROUND("AMT_INCOME_TOTAL"::numeric, 0)                         AS ingreso_anual,
        CASE
            WHEN "AMT_INCOME_TOTAL" < 100000  THEN 'A - Bajo'
            WHEN "AMT_INCOME_TOTAL" < 200000  THEN 'B - Medio-bajo'
            WHEN "AMT_INCOME_TOTAL" < 350000  THEN 'C - Medio'
            WHEN "AMT_INCOME_TOTAL" < 600000  THEN 'D - Medio-alto'
            ELSE                                   'E - Alto'
        END                                                             AS segmento_ingreso,
        "NAME_FAMILY_STATUS"                                           AS estado_civil,
        "NAME_HOUSING_TYPE"                                            AS tipo_vivienda,
        "REGION_RATING_CLIENT"                                         AS riesgo_region,
        "TARGET"                                                        AS defaulteo
    FROM application_train
""")

ejecutar("dim_producto", """
    DROP TABLE IF EXISTS dim_producto;
    CREATE TABLE dim_producto AS
    SELECT DISTINCT
        "NAME_CONTRACT_TYPE"                    AS producto_key,
        CASE "NAME_CONTRACT_TYPE"
            WHEN 'Cash loans'      THEN 'Prestamo en efectivo'
            WHEN 'Revolving loans' THEN 'Credito rotativo'
            ELSE 'Otro'
        END                                     AS descripcion_producto,
        CASE "NAME_CONTRACT_TYPE"
            WHEN 'Cash loans'      THEN 'Alto'
            WHEN 'Revolving loans' THEN 'Medio'
            ELSE 'Indefinido'
        END                                     AS nivel_riesgo
    FROM application_train
""")

ejecutar("dim_tiempo", """
    DROP TABLE IF EXISTS dim_tiempo;
    CREATE TABLE dim_tiempo AS
    SELECT DISTINCT
        "MONTHS_BALANCE"                                AS mes_key,
        ABS("MONTHS_BALANCE")                           AS meses_atras,
        CASE
            WHEN "MONTHS_BALANCE" >= -3  THEN '1. Ultimo trimestre'
            WHEN "MONTHS_BALANCE" >= -6  THEN '2. Hace 3-6 meses'
            WHEN "MONTHS_BALANCE" >= -12 THEN '3. Hace 6-12 meses'
            ELSE                              '4. Mas de 12 meses'
        END                                             AS periodo_relativo,
        CASE
            WHEN "MONTHS_BALANCE" >= -1  THEN 'Reciente'
            WHEN "MONTHS_BALANCE" >= -6  THEN 'Semestral'
            ELSE                              'Historico'
        END                                             AS agrupacion
    FROM pos_cash_balance
    ORDER BY "MONTHS_BALANCE"
""")

# ─────────────────────────────────────────────────────────────
# TABLAS DE HECHOS
# ─────────────────────────────────────────────────────────────

ejecutar("fact_pagos", """
    DROP TABLE IF EXISTS fact_pagos;
    CREATE TABLE fact_pagos AS
    SELECT
        i."SK_ID_CURR"                                                  AS cliente_key,
        i."SK_ID_PREV"                                                  AS prestamo_key,
        a."NAME_CONTRACT_TYPE"                                          AS producto_key,
        i."NUM_INSTALMENT_NUMBER"                                       AS numero_cuota,
        i."DAYS_INSTALMENT"                                             AS dia_vencimiento,
        i."DAYS_ENTRY_PAYMENT"                                          AS dia_pago_real,
        i."AMT_INSTALMENT"                                              AS monto_cuota,
        COALESCE(i."AMT_PAYMENT", 0)                                    AS monto_pagado,
        i."AMT_INSTALMENT" - COALESCE(i."AMT_PAYMENT", 0)              AS saldo_pendiente,
        CASE
            WHEN i."DAYS_ENTRY_PAYMENT" IS NULL                              THEN NULL
            ELSE i."DAYS_ENTRY_PAYMENT" - i."DAYS_INSTALMENT"
        END                                                              AS dias_atraso,
        CASE
            WHEN i."DAYS_ENTRY_PAYMENT" IS NULL                              THEN 'Sin pagar'
            WHEN i."DAYS_ENTRY_PAYMENT" <= i."DAYS_INSTALMENT"              THEN '1. A tiempo'
            WHEN (i."DAYS_ENTRY_PAYMENT" - i."DAYS_INSTALMENT") <= 30       THEN '2. Atraso leve 1-30d'
            WHEN (i."DAYS_ENTRY_PAYMENT" - i."DAYS_INSTALMENT") <= 90       THEN '3. Atraso moderado 31-90d'
            ELSE                                                              '4. Atraso grave 90+d'
        END                                                              AS bucket_pago,
        ROUND((COALESCE(i."AMT_PAYMENT",0) / NULLIF(i."AMT_INSTALMENT",0) * 100)::numeric, 1) AS pct_cobrado,
        a."NAME_INCOME_TYPE"                                             AS tipo_ingreso_cliente,
        a."NAME_EDUCATION_TYPE"                                          AS educacion_cliente,
        ROUND(ABS(a."DAYS_BIRTH") / 365.0)                             AS edad_cliente,
        CASE
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 20 AND 30 THEN '20-30 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 31 AND 40 THEN '31-40 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 41 AND 50 THEN '41-50 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 51 AND 60 THEN '51-60 anos'
            ELSE '60+ anos'
        END                                                              AS rango_edad_cliente,
        a."TARGET"                                                        AS cliente_defaulteo
    FROM installments_payments i
    LEFT JOIN application_train a ON i."SK_ID_CURR" = a."SK_ID_CURR"
""")

ejecutar("fact_aging", """
    DROP TABLE IF EXISTS fact_aging;
    CREATE TABLE fact_aging AS
    SELECT
        p."SK_ID_CURR"                                                  AS cliente_key,
        p."SK_ID_PREV"                                                  AS prestamo_key,
        p."MONTHS_BALANCE"                                              AS mes_key,
        p."SK_DPD"                                                      AS dias_mora,
        CASE
            WHEN p."SK_DPD" = 0               THEN '1. Corriente'
            WHEN p."SK_DPD" BETWEEN 1 AND 30  THEN '2. 1-30 dias'
            WHEN p."SK_DPD" BETWEEN 31 AND 60 THEN '3. 31-60 dias'
            WHEN p."SK_DPD" BETWEEN 61 AND 90 THEN '4. 61-90 dias'
            ELSE                                   '5. 90+ dias'
        END                                                             AS bucket_aging,
        p."NAME_CONTRACT_STATUS"                                        AS estado_contrato,
        p."CNT_INSTALMENT"                                              AS cuotas_totales,
        p."CNT_INSTALMENT_FUTURE"                                       AS cuotas_restantes,
        a."NAME_CONTRACT_TYPE"                                          AS tipo_producto,
        a."NAME_INCOME_TYPE"                                            AS tipo_ingreso,
        a."NAME_EDUCATION_TYPE"                                         AS educacion,
        ROUND(ABS(a."DAYS_BIRTH") / 365.0)                            AS edad,
        CASE
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 20 AND 30 THEN '20-30 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 31 AND 40 THEN '31-40 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 41 AND 50 THEN '41-50 anos'
            WHEN ABS(a."DAYS_BIRTH")/365 BETWEEN 51 AND 60 THEN '51-60 anos'
            ELSE '60+ anos'
        END                                                             AS rango_edad,
        a."AMT_CREDIT"                                                  AS monto_credito,
        a."AMT_INCOME_TOTAL"                                            AS ingreso_cliente,
        a."TARGET"                                                       AS cliente_defaulteo
    FROM pos_cash_balance p
    LEFT JOIN application_train a ON p."SK_ID_CURR" = a."SK_ID_CURR"
""")

# ─────────────────────────────────────────────────────────────
# VERIFICACION FINAL
# ─────────────────────────────────────────────────────────────
print("\n" + "="*55)
print("  VERIFICACION DEL MODELO")
print("="*55)

tablas_mart = ["dim_cliente","dim_producto","dim_tiempo","fact_pagos","fact_aging"]
with engine.connect() as c:
    for t in tablas_mart:
        filas = c.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
        cols  = c.execute(text(f"SELECT COUNT(*) FROM information_schema.columns WHERE table_name='{t}'")).scalar()
        print(f"  {t:<20} {filas:>8,} filas   {cols:>3} cols")

print("\n  Modelo Star Schema listo.")
print("="*55)
