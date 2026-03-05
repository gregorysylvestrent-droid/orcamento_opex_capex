# Dashboard OPEX vs CAPEX (Flask + Plotly)

Este projeto gera um dashboard web para acompanhar despesas OPEX/CAPEX a partir de um Excel (aba **Logística**).

## 1) Estrutura
- `app.py` (entrada do Flask)
- `services/data.py` (carregamento, limpeza, filtros, insights)
- `templates/` (HTML com Bootstrap + Plotly)
- `static/` (CSS e JS)
- `data/` (onde você pode colocar o Excel e o budget)

## 2) Como rodar (Windows)
```bash
cd opex_capex_flask
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
```

Abra: http://127.0.0.1:5000

## 3) Excel de origem
Por padrão o app tenta ler:
- `data/OPEX e CAPEX.xlsx` (aba `Logística`)

Você pode:
- substituir esse arquivo na pasta `data/`, **ou**
- subir um novo via página **Upload**.

## 4) Orçamento (para comparar com Realizado)
Quando você tiver o orçamento, você pode:
- subir um arquivo (Excel/CSV) com colunas: `Mes` (YYYY-MM), `OPEX`, `CAPEX`
- ou preencher manualmente na página **Orçamento**

O app calcula variação (R$ e %) por mês e no total.

## 5) Observações
- O app faz cache do Excel e recarrega quando o arquivo muda.
- Os filtros (período, unidade, área, tipo) são aplicados em todas as visões.

