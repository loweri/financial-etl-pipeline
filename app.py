import os
import glob
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="Financial Data Warehouse — Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Carregar variáveis de ambiente
load_dotenv()
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

# CSS personalizado para visual moderno e limpo
st.markdown("""
<style>
    .metric-card {
        background-color: #1E222D;
        border-radius: 8px;
        padding: 16px;
        border: 1px solid #2A2E39;
    }
    .stMetric label {
        color: #94A3B8 !important;
        font-size: 0.9rem !important;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def load_data():
    """
    Carrega os dados do Data Warehouse no Supabase PostgreSQL.
    Se não houver conexão de banco disponível, faz fallback automático para os CSVs processados.
    """
    df = pd.DataFrame()

    # Tentativa 1: Conectar diretamente ao Supabase PostgreSQL
    if SUPABASE_DB_URL:
        try:
            engine = create_engine(SUPABASE_DB_URL)
            query = """
                SELECT 
                    f.ticker_code,
                    f.date,
                    f.open_price,
                    f.high_price,
                    f.low_price,
                    f.close_price,
                    f.volume,
                    d.company_name,
                    d.sector
                FROM fact_stock_prices f
                LEFT JOIN dim_tickers d ON f.ticker_code = d.ticker_code
                ORDER BY f.ticker_code, f.date ASC;
            """
            df = pd.read_sql(query, con=engine)
            if not df.empty:
                df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
                return df, "Supabase PostgreSQL (Cloud DW)"
        except Exception as e:
            st.sidebar.warning(f"Fallback para dados locais: {str(e)[:50]}...")

    # Tentativa 2: Fallback local (data/processed/*.csv)
    arquivos = glob.glob("data/processed/*_processed.csv")
    dfs = []
    for arq in arquivos:
        ticker = os.path.basename(arq).replace("_processed.csv", "")
        temp_df = pd.read_csv(arq)
        temp_df['ticker_code'] = ticker
        
        # Mapeamento simples de nome/setor
        nomes = {
            "PETR4.SA": ("Petrobras", "Petróleo e Gás"),
            "VALE3.SA": ("Vale S.A.", "Mineração"),
            "ITUB4.SA": ("Itaú Unibanco", "Financeiro"),
            "AAPL": ("Apple Inc.", "Tecnologia"),
            "NVDA": ("NVIDIA Corp.", "Semicondutores"),
            "TSLA": ("Tesla Inc.", "Automotivo / Tech")
        }
        nome, setor = nomes.get(ticker, (ticker, "Geral"))
        temp_df['company_name'] = nome
        temp_df['sector'] = setor
        dfs.append(temp_df)

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # Padroniza nomes de colunas
        col_map = {
            "Date": "date", "Open": "open_price", "High": "high_price",
            "Low": "low_price", "Close": "close_price", "Volume": "volume"
        }
        df = df.rename(columns=col_map)
        df['date'] = pd.to_datetime(df['date'], utc=True).dt.tz_localize(None)
        return df, "Local Storage (data/processed/)"

    return pd.DataFrame(), "Sem Dados"


# Carregamento dos dados
df_all, source_name = load_data()

# Header Principal
st.title("📊 Financial Data Warehouse — Dashboard de Cotações")
st.caption(f"Pipeline ETL automatizado com Pandas, PostgreSQL e Apache Airflow 3 · Fonte de dados: **{source_name}**")

if df_all.empty:
    st.error("❌ Nenhum dado encontrado. Execute o pipeline de extração e transformação primeiro!")
    st.stop()

# Barra Lateral: Filtros
st.sidebar.header("⚙️ Filtros e Configurações")

# Seleção de Ativo
tickers_disponiveis = sorted(df_all['ticker_code'].unique().tolist())
ticker_selecionado = st.sidebar.selectbox(
    "📌 Selecione o Ativo:",
    options=tickers_disponiveis,
    index=0
)

# Filtro de Data
df_ticker = df_all[df_all['ticker_code'] == ticker_selecionado].sort_values(by='date').copy()

min_date = df_ticker['date'].min().date()
max_date = df_ticker['date'].max().date()

data_inicio, data_fim = st.sidebar.date_input(
    "📅 Intervalo de Datas:",
    value=[min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Filtrar pelo período
df_filtrado = df_ticker[
    (df_ticker['date'].dt.date >= data_inicio) & 
    (df_ticker['date'].dt.date <= data_fim)
].copy()

if df_filtrado.empty:
    st.warning("⚠️ Nenhum dado no intervalo de datas selecionado.")
    st.stop()

# Informações do Ativo
company_name = df_filtrado['company_name'].iloc[0] if 'company_name' in df_filtrado.columns else ticker_selecionado
sector = df_filtrado['sector'].iloc[0] if 'sector' in df_filtrado.columns else "N/A"

st.subheader(f"{ticker_selecionado} — {company_name} ({sector})")

# Métricas Principais (Cards KPI)
col1, col2, col3, col4 = st.columns(4)

ultimo_preco = df_filtrado['close_price'].iloc[-1]
primeiro_preco = df_filtrado['close_price'].iloc[0]
variacao_periodo_pct = ((ultimo_preco - primeiro_preco) / primeiro_preco) * 100

preco_max = df_filtrado['high_price'].max()
preco_min = df_filtrado['low_price'].min()
volume_medio = df_filtrado['volume'].mean()

with col1:
    st.metric(
        label="Último Fechamento",
        value=f"R$ {ultimo_preco:.2f}" if ".SA" in ticker_selecionado else f"$ {ultimo_preco:.2f}",
        delta=f"{variacao_periodo_pct:+.2f}% no período"
    )

with col2:
    st.metric(
        label="Máxima no Período",
        value=f"R$ {preco_max:.2f}" if ".SA" in ticker_selecionado else f"$ {preco_max:.2f}"
    )

with col3:
    st.metric(
        label="Mínima no Período",
        value=f"R$ {preco_min:.2f}" if ".SA" in ticker_selecionado else f"$ {preco_min:.2f}"
    )

with col4:
    st.metric(
        label="Volume Médio Diário",
        value=f"{volume_medio:,.0f}"
    )

st.markdown("---")

# Abas de Visualização
tab1, tab2, tab3 = st.tabs(["📈 Gráfico de Cotação", "🕯️ Gráfico Candlestick", "📋 Tabela de Dados Históricos"])

with tab1:
    # Gráfico de Linha com Médias Móveis
    df_filtrado['SMA_21'] = df_filtrado['close_price'].rolling(window=21).mean()
    df_filtrado['SMA_50'] = df_filtrado['close_price'].rolling(window=50).mean()

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=df_filtrado['date'], y=df_filtrado['close_price'],
        mode='lines', name='Fechamento',
        line=dict(color='#00D4FF', width=2)
    ))
    fig_line.add_trace(go.Scatter(
        x=df_filtrado['date'], y=df_filtrado['SMA_21'],
        mode='lines', name='Média Móvel (21d)',
        line=dict(color='#FFA500', width=1.5, dash='dot')
    ))
    fig_line.add_trace(go.Scatter(
        x=df_filtrado['date'], y=df_filtrado['SMA_50'],
        mode='lines', name='Média Móvel (50d)',
        line=dict(color='#FF4B4B', width=1.5, dash='dash')
    ))

    fig_line.update_layout(
        title=f"Evolução de Preço — {ticker_selecionado}",
        xaxis_title="Data",
        yaxis_title="Preço (USD / BRL)",
        template="plotly_dark",
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_line, use_container_width=True)

with tab2:
    # Gráfico Candlestick (Velas)
    fig_candle = go.Figure(data=[go.Candlestick(
        x=df_filtrado['date'],
        open=df_filtrado['open_price'],
        high=df_filtrado['high_price'],
        low=df_filtrado['low_price'],
        close=df_filtrado['close_price'],
        name='Candles'
    )])

    fig_candle.update_layout(
        title=f"Velas Diárias (Candlestick) — {ticker_selecionado}",
        xaxis_title="Data",
        yaxis_title="Preço",
        template="plotly_dark",
        height=500,
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig_candle, use_container_width=True)

with tab3:
    st.dataframe(
        df_filtrado[['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']].sort_values(by='date', ascending=False),
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")
st.caption("Desenvolvido por **Ericles Fernandes Oliveira** · Engenharia de Dados")
