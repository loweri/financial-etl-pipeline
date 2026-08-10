import os
import glob
import time
import logging
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger(__name__)

# 1. Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

db_url = os.getenv("SUPABASE_DB_URL")

if not db_url:
    log.error("❌ SUPABASE_DB_URL não foi encontrada no arquivo .env!")
    exit(1)

log.info("🔌 Conectando ao Data Warehouse no Supabase...")
engine = create_engine(db_url)

start_time = time.time()
total_rows_processed = 0
null_count = 0

try:
    arquivos_processed = glob.glob("data/processed/*_processed.csv")
    
    if not arquivos_processed:
        log.warning("⚠️ Nenhum arquivo encontrado em data/processed/")
        exit(0)

    for caminho_arquivo in arquivos_processed:
        nome_arquivo = os.path.basename(caminho_arquivo)
        ticker_code = nome_arquivo.replace("_processed.csv", "")
        
        log.info(f"📦 Carregando dados do ativo: {ticker_code}...")
        df = pd.read_csv(caminho_arquivo)
        
        if df.empty:
            continue
            
        total_rows_processed += len(df)
        null_count += df["Close"].isnull().sum()
        
        with engine.begin() as conn:
            # 1. Inserir/Garantir Registro na dim_ticker (SCD Tipo 2)
            conn.execute(text("""
                INSERT INTO dim_ticker (ticker_code, company_name, sector, industry, country, valid_from, is_current)
                VALUES (:ticker, :company, 'Finance/Tech', 'Market Data', 'BR/US', CURRENT_DATE, TRUE)
                ON CONFLICT (ticker_code, is_current) DO NOTHING
            """), {"ticker": ticker_code, "company": ticker_code})

            # Pegar o ticker_key gerado
            result = conn.execute(
                text("SELECT ticker_key FROM dim_ticker WHERE ticker_code = :t AND is_current = TRUE"),
                {"t": ticker_code}
            ).fetchone()
            
            ticker_key = result[0]

            # 2. Inserir datas na dim_date e cotações na fact_stock_prices
            for _, row in df.iterrows():
                # Formata a data (Ex: 2025-08-07)
                date_str = str(row["Date"]).split(" ")[0]
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                date_key = int(date_obj.strftime("%Y%m%d"))
                
                # Inserir na dim_date se não existir
                conn.execute(text("""
                    INSERT INTO dim_date (date_key, full_date, year, month, month_name, day, day_name, is_weekend)
                    VALUES (:key, :date, :year, :month, :mname, :day, :dname, :is_weekend)
                    ON CONFLICT (date_key) DO NOTHING
                """), {
                    "key": date_key,
                    "date": date_obj,
                    "year": date_obj.year,
                    "month": date_obj.month,
                    "mname": date_obj.strftime("%B"),
                    "day": date_obj.day,
                    "dname": date_obj.strftime("%A"),
                    "is_weekend": date_obj.isoweekday() >= 6
                })

                # Inserir ou Atualizar na fact_stock_prices (Carga Idempotente)
                conn.execute(text("""
                    INSERT INTO fact_stock_prices
                        (ticker_key, date_key, open_price, close_price, high_price, low_price,
                         volume, daily_return_pct, sma_21, sma_200)
                    VALUES
                        (:t_key, :d_key, :open, :close, :high, :low, :vol, :ret, :sma21, :sma200)
                    ON CONFLICT (ticker_key, date_key) DO UPDATE SET
                        close_price      = EXCLUDED.close_price,
                        volume           = EXCLUDED.volume,
                        daily_return_pct = EXCLUDED.daily_return_pct,
                        sma_21           = EXCLUDED.sma_21,
                        sma_200          = EXCLUDED.sma_200
                """), {
                    "t_key": ticker_key,
                    "d_key": date_key,
                    "open": float(row["Open"]) if pd.notnull(row["Open"]) else None,
                    "close": float(row["Close"]) if pd.notnull(row["Close"]) else None,
                    "high": float(row["High"]) if pd.notnull(row["High"]) else None,
                    "low": float(row["Low"]) if pd.notnull(row["Low"]) else None,
                    "vol": int(row["Volume"]) if pd.notnull(row["Volume"]) else 0,
                    "ret": float(row["daily_return_pct"]) if pd.notnull(row["daily_return_pct"]) else None,
                    "sma21": float(row["sma_21"]) if pd.notnull(row["sma_21"]) else None,
                    "sma200": float(row["sma_200"]) if pd.notnull(row["sma_200"]) else None
                })
        
        log.info(f"  ✨ {ticker_code} carregado com sucesso no Supabase!")

    # 3. Gravar Log de Auditoria na dw_audit_log (Observabilidade)
    duration = round(time.time() - start_time, 2)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO dw_audit_log (dag_id, run_id, execution_date, rows_processed, null_count, status, duration_seconds, message)
            VALUES ('manual_etl_load', :run_id, CURRENT_TIMESTAMP, :rows, :nulls, 'SUCCESS', :dur, 'Carga inicial do DW executada com sucesso.')
        """), {
            "run_id": f"run_{int(time.time())}",
            "rows": total_rows_processed,
            "nulls": int(null_count),
            "dur": duration
        })

    log.info(f"🎉 CARGA COMPLETA NO DATA WAREHOUSE! Total de linhas: {total_rows_processed} em {duration}s.")

except Exception as e:
    duration = round(time.time() - start_time, 2)
    log.error(f"❌ FALHA NA CARGA DO DW: {e}")
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO dw_audit_log (dag_id, run_id, execution_date, rows_processed, null_count, status, duration_seconds, message)
                VALUES ('manual_etl_load', :run_id, CURRENT_TIMESTAMP, 0, 0, 'FAILED', :dur, :msg)
            """), {
                "run_id": f"run_{int(time.time())}",
                "dur": duration,
                "msg": str(e)[:250]
            })
    except Exception as audit_err:
        log.error(f"Erro ao gravar log de falha: {audit_err}")
