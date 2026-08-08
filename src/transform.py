import pandas as pd
import glob
import os

print("🧪 Iniciando transformação e cálculo de indicadores...")

# Pega todos os arquivos CSV na pasta data/raw
arquivos_raw = glob.glob("data/raw/*_raw.csv")

for caminho_arquivo in arquivos_raw:
    nome_arquivo = os.path.basename(caminho_arquivo)
    ticker = nome_arquivo.replace("_raw.csv", "")
    
    print(f"📊 Transformando dados de {ticker}...")
    
    # 1. Carrega o CSV bruto no Pandas
    df = pd.read_csv(caminho_arquivo)
    
    # 2. Calcula os indicadores técnicos do desafio
    df["daily_return_pct"] = ((df["Close"] - df["Open"]) / df["Open"]) * 100
    df["sma_21"] = df["Close"].rolling(window=21).mean()
    df["sma_200"] = df["Close"].rolling(window=200).mean()
    
    # 3. Define o caminho da camada Silver (processed)
    caminho_processado = f"data/processed/{ticker}_processed.csv"
    
    # 4. Salva o dado transformado
    df.to_csv(caminho_processado, index=False)
    print(f"  ✨ Salvo na Camada Silver: {caminho_processado}")

print("\n🎉 Transformação concluída com sucesso!")
