"""
============================================================
FINANCIAL ETL PIPELINE — AIRFLOW ORCHESTRATION DAG
============================================================
DAG responsável por agendar, orquestrar e monitorar a esteira
completa de dados financeiros (Bronze -> Silver -> Gold DW).

Padrões de Produção:
  - Resolução dinâmica de PROJECT_DIR via pathlib e variáveis de ambiente.
  - Idempotência no PostgreSQL Supabase via ON CONFLICT DO UPDATE.
  - Agendamento: De segunda a sexta-feira às 21:00 BRT (pós-fechamento dos mercados).
============================================================
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
try:
    from airflow.providers.standard.operators.bash import BashOperator
except ImportError:
    from airflow.operators.bash import BashOperator


def _resolve_project_dir() -> str:
    """Resolve o PROJECT_DIR usando múltiplas estratégias de fallback."""
    env_dir = os.environ.get("FINANCIAL_PROJECT_DIR", "")
    if env_dir and Path(env_dir, "src").is_dir():
        return env_dir

    candidate = str(Path(__file__).resolve().parent.parent)
    if Path(candidate, "src").is_dir():
        return candidate

    return str(Path.cwd())


# Diretório do projeto resolvido dinamicamente (portável entre máquinas)
PROJECT_DIR = _resolve_project_dir()

# Detecção dinâmica do executável python do ambiente virtual
venv_candidate = Path(PROJECT_DIR) / ".venv" / "bin" / "python3"
VENV_PYTHON = str(venv_candidate) if venv_candidate.exists() else "python3"


# Configurações padrão da DAG (Resiliência & Retry Policy)
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=10),
    "start_date": datetime(2026, 1, 1),
}

with DAG(
    dag_id="financial_etl_pipeline_dw",
    default_args=default_args,
    description="Pipeline ETL de Cotações Financeiras (yfinance -> Pandas -> Supabase DW)",
    schedule="0 21 * * 1-5",
    catchup=False,
    tags=["finance", "etl", "supabase", "medallion", "market-data"],
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

    # Definição do Fluxo de Dependência da DAG
    task_extract >> task_transform >> task_load
