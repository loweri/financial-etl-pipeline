# 📊 Financial ETL Pipeline — Market Data Ingestion & Transformation

![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python)
![Pandas](https://img.shields.io/badge/Pandas-3.0-150458?logo=pandas)
![Git](https://img.shields.io/badge/Git-Version_Control-F05032?logo=git)
![License](https://img.shields.io/badge/license-MIT-green)

Automated Data Engineering pipeline designed to extract historical stock market data via `yfinance`, apply technical indicators using **Pandas**, and organize the data adhering to the **Medallion Architecture (Bronze & Silver Layers)**.

---

## 🏗️ Pipeline Architecture

```mermaid
flowchart TD
    subgraph Ingestao ["1. Camada de Ingestão"]
        API["API yfinance\n(Yahoo Finance)"]
        PY_EXT["src/extract.py\n(Script Python)"]
        API --> PY_EXT
    end

    subgraph Bronze ["2. Camada Bronze (Raw Data)"]
        RAW["data/raw/\n(*_raw.csv)"]
        PY_EXT -->|Salva CSVs brutos| RAW
    end

    subgraph Silver ["3. Camada Silver (Processed Data)"]
        PY_TRF["src/transform.py\n(Pandas Engine)"]
        PROC["data/processed/\n(*_processed.csv)"]
        RAW -->|Lê arquivos brutos| PY_TRF
        PY_TRF -->|Cálculo de Indicadores| PROC
    end

    subgraph Indicadores ["Indicadores Técnicos Calculados"]
        IND1["daily_return_pct\n(Retorno Diário %)"]
        IND2["sma_21\n(Média Móvel 21 dias)"]
        IND3["sma_200\n(Média Móvel 200 dias)"]
        PY_TRF -.-> IND1
        PY_TRF -.-> IND2
        PY_TRF -.-> IND3
    end
```

---

## 📂 Project Structure

```text
financial-etl-pipeline/
├── .venv/                   # Local Python Virtual Environment (Ignored)
├── .gitignore               # Version control rules
├── README.md                # Project documentation
│
├── src/
│   ├── extract.py           # Ingestion script for yfinance tickers
│   └── transform.py         # Pandas transformation engine
│
└── data/
    ├── raw/                 # Bronze Layer: Untouched raw market CSVs
    ├── processed/           # Silver Layer: Transformed CSVs with indicators
    └── exports/             # Gold Layer: Ready for consumption (Upcoming)
```

---

## ⚡ Tracked Assets

The pipeline monitors real-time and historical daily data for the following portfolio:

- **B3 (Brasil):** `PETR4.SA`, `VALE3.SA`, `ITUB4.SA`
- **US Markets:** `AAPL`, `NVDA`, `TSLA`

---

## 🚀 How to Run Locally

### 1. Prerequisites & Virtual Environment
```bash
# Clone the repository
git clone https://github.com/loweri/financial-etl-pipeline.git
cd financial-etl-pipeline

# Create & Activate Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Install Dependencies
pip install yfinance pandas
```

### 2. Execute Ingestion (Bronze Layer)
```bash
python3 src/extract.py
```

### 3. Execute Transformation (Silver Layer)
```bash
python3 src/transform.py
```

---

## 👨‍💻 Author

**Ericles (loweri)** — *Data Engineer*
