# Dashboard OPEX vs CAPEX (Flask + Plotly)

Este projeto gera um dashboard web para acompanhar despesas OPEX/CAPEX a partir de um Excel (aba **Logística**), com filtros e comparação entre realizado e orçamento.

## 📁 Estrutura do projeto
- `app.py`: ponto de entrada da aplicação Flask.
- `services/data.py`: leitura, limpeza, filtros e consolidação dos dados.
- `templates/`: páginas HTML (Bootstrap + Plotly).
- `static/`: estilos e scripts JavaScript.
- `data/`: arquivos de entrada (Excel e orçamento).

## ▶️ Como executar (Windows)
No diretório do projeto:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
set FLASK_APP=app.py
set FLASK_ENV=development
flask run
```

Acesse no navegador: `http://127.0.0.1:5000`

## 📄 Fonte de dados (Excel)
Por padrão, o app tenta ler:
- `data/OPEX e CAPEX.xlsx` (aba `Logística`)

Você pode:
- substituir esse arquivo dentro da pasta `data/`, **ou**
- subir um novo pela página **Upload**.

## 💰 Orçamento (comparação com realizado)
Você pode informar o orçamento de duas formas:
- subir um arquivo Excel/CSV com colunas `Mes` (YYYY-MM), `OPEX`, `CAPEX`; ou
- preencher manualmente pela página **Orçamento**.

O app calcula automaticamente variação mensal e total (R$ e %).

## ✅ Observações gerais
- O app usa cache para o Excel e recarrega quando o arquivo muda.
- Filtros de período, unidade, área e tipo são aplicados em todas as visões.

## 🛠️ Observações extras para ambiente Windows (quando houver bloqueios)
Se houver problema com ambiente virtual, execução de scripts ou bloqueio por arquivos baixados, siga os passos abaixo.

### Passo A — mover o projeto para uma pasta “limpa”
Crie a pasta:

```powershell
mkdir C:\Dev\opex_capex_flask
```

Copie o projeto para lá (ex.: via Explorer com Ctrl+C/Ctrl+V) e abra o `cmd` em:

```text
C:\Dev\opex_capex_flask\opex_capex_flask
```

### Passo B — remover “Mark of the Web” (MOTW)
No PowerShell (geralmente sem precisar de admin):

```powershell
Get-ChildItem -Recurse C:\Dev\opex_capex_flask | Unblock-File
```

### Passo C — recriar a virtualenv e reinstalar dependências
Recrie a `.venv` com `virtualenv`:

```cmd
rmdir /s /q .venv
C:\Users\gregory.sylvestre\python312\python.exe -m virtualenv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Se a política da máquina bloquear apenas arquivos com MOTW/Downloads, esse fluxo normalmente resolve.