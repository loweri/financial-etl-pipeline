import yfinance as yf
import os
TICKERS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "AAPL", "NVDA", "TSLA"]
print("🚀 Iniciando extração da lista de ativos...")
for ticker in TICKERS:
    print(f"📦 Extraindo dados de {ticker}...")
    obj = yf.Ticker(ticker)
    df = obj.history(period="1y")
    
    if not df.empty:
        # Salva o arquivo CSV bruto na pasta data/raw
        caminho_arquivo = f"data/raw/{ticker}_raw.csv"
        df.to_csv(caminho_arquivo)
        print(f"  ✅ Salvo com sucesso em: {caminho_arquivo}")
    else:
        print(f"  ⚠️ Nenhum dado encontrado para {ticker}")
print("\n🎉 Extração concluída!")
