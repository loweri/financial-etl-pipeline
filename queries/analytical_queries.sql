-- ============================================================
-- FINANCIAL ETL PIPELINE — CONSULTAS ANALÍTICAS & OBSERVABILIDADE
-- Data Warehouse: Supabase (PostgreSQL Cloud)
-- Modelo: Star Schema Kimball
-- ============================================================

-- 1. RANKING DE RENTABILIDADE ACUMULADA DOS ATIVOS
-- Calcula a menor e maior cotação do período e o retorno percentual acumulado.
SELECT
    t.ticker_code AS ativo,
    t.company_name AS empresa,
    MIN(f.close_price) AS preco_minimo,
    MAX(f.close_price) AS preco_maximo,
    ROUND(((MAX(f.close_price) - MIN(f.close_price)) / MIN(f.close_price) * 100), 2) AS rentabilidade_pct
FROM fact_stock_prices f
JOIN dim_ticker t ON f.ticker_key = t.ticker_key AND t.is_current = TRUE
GROUP BY t.ticker_code, t.company_name
ORDER BY rentabilidade_pct DESC;


-- 2. SINAL DE TENDÊNCIA TÉCNICA (GOLDEN CROSS / MÉDIAS MÓVEIS)
-- Avalia se a média móvel de 21 dias está acima da média móvel de 200 dias (Tendência de Alta vs Baixa).
SELECT
    d.full_date AS data,
    t.ticker_code AS ativo,
    f.close_price AS preco_fechamento,
    f.sma_21 AS media_21_dias,
    f.sma_200 AS media_200_dias,
    CASE
        WHEN f.sma_21 > f.sma_200 THEN 'Tendência de Alta 📈'
        WHEN f.sma_21 < f.sma_200 THEN 'Tendência de Baixa 📉'
        ELSE 'Neutro ➖'
    END AS sinal_tecnico
FROM fact_stock_prices f
JOIN dim_ticker t ON f.ticker_key = t.ticker_key AND t.is_current = TRUE
JOIN dim_date   d ON f.date_key   = d.date_key
WHERE t.ticker_code = 'PETR4.SA' AND f.sma_200 IS NOT NULL
ORDER BY d.full_date DESC
LIMIT 15;


-- 3. TELEMETRIA E HISTÓRICO DE AUDITORIA DO PIPELINE (OBSERVABILIDADE)
-- Monitora status de execução, linhas processadas, nulos e tempo de execução.
SELECT
    audit_key,
    dag_id,
    execution_date AS data_execucao,
    rows_processed AS linhas_processadas,
    null_count AS quantidade_nulos,
    status,
    duration_seconds AS duracao_segundos,
    message AS mensagem
FROM dw_audit_log
ORDER BY execution_date DESC
LIMIT 10;
