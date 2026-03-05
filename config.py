import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_EXCEL_PATH = os.path.join(DATA_DIR, "OPEX e CAPEX.xlsx")
DEFAULT_SHEET_NAME = "Logística"

# Budget table (generated/imported). See services/data.py
BUDGET_PATH = os.path.join(DATA_DIR, "budget.csv")

# Optional: place your budget sources here (or import via UI)
BUDGET_OPEX_2026_PATH = os.path.join(DATA_DIR, "OPEX 2026.xlsx")
BUDGET_CAPEX_LOG_PATH = os.path.join(DATA_DIR, "CAPEX 2026 - LOGÍSTICA.xlsx")
BUDGET_CAPEX_STARLINK_PATH = os.path.join(DATA_DIR, "CAPEX - Locação de Antenas Starlink.xlsx")

# Ajuste se precisar (ex.: produção)
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "troque-esta-chave-em-producao")
