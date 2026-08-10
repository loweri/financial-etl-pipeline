"""
============================================================
FINANCIAL ETL PIPELINE — AIRFLOW ORCHESTRATION DAG
============================================================
DAG responsável por agendar, orquestrar e monitorar a esteira
completa de dados financeiros (Bronze -> Silver -> Gold DW).

Agendamento: De segunda a sexta-feira às 21:00 BRT (pós-fechamento dos mercados).
============================================================
"""

import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator

# Diretório raiz do projeto no ambiente Linux/WSL
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(PROJECT_DIR, ".venv", "bin", "python3")

# Configurações padrão da DAG (Resiliência & Retry Policy)
default_args = {
    "owner": "ericles_oliveira",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,                             # Se falhar (ex: queda da API yfinance), tenta 2 vezes
    "retry_delay": timedelta(minutes=5),      # Aguarda 5 minutos entre as tentativas
    "start_date": datetime(2026, 1, 1),
}

with DAG(
    dag_id="financial_etl_pipeline_dw",
    default_args=default_args,
    description="Pipeline ETL de Cotações Financeiras (yfinance -> Pandas -> Supabase DW)",
    schedule_interval="0 21 * * 1-5",         # Cron: 21:00 de Segunda a Sexta
    catchup=False,                            # Não executa datas passadas retroativamente
    tags=["finance", "etl", "supabase", "medallion"],
) as dag:

    # 1. Tarefa de Ingestão (Camada Bronze)
    task_extract = BashOperator(
        task_id="extract_market_data",
        bash_command=f"cd {PROJECT_DIR} && {VENV_PYTHON} src/extract.py",
    )

    # 2. Tarefa de Transformação (Camada Silver)
    task_transform = BashOperator(
        task_id="transform_market_data",
        bash_command=f"cd {PROJECT_DIR} && {VENV_PYTHON} src/transform.py",
    )

    # 3. Tarefa de Carga no Data Warehouse (Camada Gold)
    task_load = BashOperator(
        task_id="load_dw_supabase",
        bash_command=f"cd {PROJECT_DIR} && {VENV_PYTHON} src/load.py",
    )

    # Definição do Fluxo de Dependência da DAG (Grafo Acíclico Dirigido)
    task_extract >> task_transform >> task_load
