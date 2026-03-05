import os
from functools import lru_cache
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import pandas as pd
import numpy as np

from config import DEFAULT_EXCEL_PATH, DEFAULT_SHEET_NAME, BUDGET_PATH, BUDGET_OPEX_2026_PATH, BUDGET_CAPEX_LOG_PATH, BUDGET_CAPEX_STARLINK_PATH


# ----------------------------
# Utilidades
# ----------------------------

MONEY_COL = "Vlr.Total"
DATE_COL = "Data Emissao"
BUDGET_MONTH_COL = "Mes"
BUDGET_CC_CODE_COL = "C. CUSTOS"
BUDGET_AREA_COL = "ÁREA"

DEFAULT_COLS = [
    "Numero", "Data Emissao", "Fornecedor", "Descricao", "Unidade", "Quantidade",
    "Vlr.Total", "PLACA VEICUL", "Tpo.Manuten.", "Centro Custo", "Descr CC",
    "Observacoes", "Cta Contabil", "Vl. Desconto", "Grupo", "Gr. Compras",
    "Status do ME", "Origem", "Unidade2", "Área", "Cta. Descrição", "Tipo Orçamento"
]


def _safe_str(s):
    if pd.isna(s):
        return ""
    return str(s).strip()


def _normalize_tipo_orc(x: str) -> str:
    x = _safe_str(x).upper()
    if "CAPEX" in x:
        return "CAPEX"
    if "OPEX" in x:
        return "OPEX"
    return "N/I"


def _coerce_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def _coerce_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _month_str(dt_series: pd.Series) -> pd.Series:
    # YYYY-MM
    return dt_series.dt.to_period("M").astype(str)


@dataclass(frozen=True)
class DataMeta:
    excel_path: str
    sheet_name: str
    mtime: float


def get_default_source() -> Tuple[str, str]:
    return DEFAULT_EXCEL_PATH, DEFAULT_SHEET_NAME


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Mantém o que existe e garante colunas esperadas (sem quebrar)
    for c in DEFAULT_COLS:
        if c not in df.columns:
            df[c] = np.nan
    return df


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = ensure_columns(df)

    df[DATE_COL] = _coerce_datetime(df[DATE_COL])
    if "Data Lanc" in df.columns:
        df["Data Lanc"] = _coerce_datetime(df["Data Lanc"])

    df[MONEY_COL] = _coerce_numeric(df[MONEY_COL])
    if "Vl. Desconto" in df.columns:
        df["Vl. Desconto"] = _coerce_numeric(df["Vl. Desconto"])
    if "Quantidade" in df.columns:
        df["Quantidade"] = _coerce_numeric(df["Quantidade"])

    df["Tipo Orçamento"] = df["Tipo Orçamento"].apply(_normalize_tipo_orc)

    # Derivações
    df["Mes"] = _month_str(df[DATE_COL])
    df["Ano"] = df[DATE_COL].dt.year

    # Campos texto normalizados (facilita filtros)
    for col in ["Fornecedor", "Descr CC", "Cta. Descrição", "Grupo", "Gr. Compras", "Unidade2", "Área", "PLACA VEICUL", "Descricao"]:
        if col in df.columns:
            df[col] = df[col].apply(_safe_str)

    if "Centro Custo" in df.columns:
        df["Centro Custo"] = df["Centro Custo"].apply(lambda x: str(x).strip().replace(".0","") if pd.notna(x) else "")
    
    return df


def _source_meta(excel_path: str, sheet_name: str) -> DataMeta:
    mtime = os.path.getmtime(excel_path) if os.path.exists(excel_path) else 0.0
    return DataMeta(excel_path=excel_path, sheet_name=sheet_name, mtime=mtime)


@lru_cache(maxsize=8)
def _load_cached(excel_path: str, sheet_name: str, mtime: float) -> pd.DataFrame:
    # mtime entra na chave do cache para invalidar quando arquivo mudar
    if not os.path.exists(excel_path):
        # Retorna DF vazio, mas com colunas esperadas
        return clean_df(pd.DataFrame(columns=DEFAULT_COLS))

    df = pd.read_excel(excel_path, sheet_name=sheet_name, engine="openpyxl")
    return clean_df(df)


def load_data(excel_path: str, sheet_name: str) -> pd.DataFrame:
    meta = _source_meta(excel_path, sheet_name)
    return _load_cached(meta.excel_path, meta.sheet_name, meta.mtime)


def apply_filters(
    df: pd.DataFrame,
    start: Optional[str] = None,
    end: Optional[str] = None,
    tipo_orc: Optional[str] = None,
    unidade2: Optional[str] = None,
    area: Optional[str] = None,
) -> pd.DataFrame:
    out = df.copy()

    # Datas (inclusivo)
    if start:
        start_dt = pd.to_datetime(start, errors="coerce")
        if pd.notna(start_dt):
            out = out[out[DATE_COL] >= start_dt]
    if end:
        end_dt = pd.to_datetime(end, errors="coerce")
        if pd.notna(end_dt):
            out = out[out[DATE_COL] <= end_dt]

    if tipo_orc and tipo_orc != "ALL":
        out = out[out["Tipo Orçamento"] == tipo_orc]

    if unidade2 and unidade2 != "ALL":
        out = out[out["Unidade2"] == unidade2]

    if area and area != "ALL":
        out = out[out["Área"] == area]

    return out


def kpis(df: pd.DataFrame) -> Dict:
    total = float(df[MONEY_COL].sum(skipna=True))
    qtd = int(df.shape[0])
    fornecedores = int(df["Fornecedor"].nunique())
    centros_custo = int(df["Descr CC"].nunique())
    placas = int(df["PLACA VEICUL"].nunique())

    desconto = float(df.get("Vl. Desconto", pd.Series(dtype=float)).sum(skipna=True))
    desconto_pct = float((desconto / total) * 100) if total else 0.0

    return {
        "total": total,
        "linhas": qtd,
        "fornecedores": fornecedores,
        "centros_custo": centros_custo,
        "placas": placas,
        "desconto": desconto,
        "desconto_pct": desconto_pct,
    }


def breakdown(df: pd.DataFrame, col: str, top_n: int = 10) -> pd.DataFrame:
    if col not in df.columns:
        return pd.DataFrame(columns=[col, "Valor"])
    g = (
        df.groupby(col, dropna=False)[MONEY_COL]
        .sum(min_count=1)
        .sort_values(ascending=False)
        .head(top_n)
        .reset_index()
        .rename(columns={MONEY_COL: "Valor"})
    )
    return g


def timeseries(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Mes", "Tipo Orçamento", "Valor"])
    g = (
        df.groupby(["Mes", "Tipo Orçamento"], dropna=False)[MONEY_COL]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={MONEY_COL: "Valor"})
        .sort_values(["Mes", "Tipo Orçamento"])
    )
    return g


def share_opex_capex(df: pd.DataFrame) -> pd.DataFrame:
    g = (
        df.groupby("Tipo Orçamento")[MONEY_COL]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={MONEY_COL: "Valor"})
        .sort_values("Valor", ascending=False)
    )
    return g


def outliers_iqr(df: pd.DataFrame, group_col: str = "Cta. Descrição", min_group_n: int = 20, top_n: int = 30) -> pd.DataFrame:
    """
    Encontra possíveis outliers por grupo (ex.: por conta/categoria), usando IQR.
    Útil para identificar itens muito acima do padrão da categoria.
    """
    if df.empty or group_col not in df.columns:
        return pd.DataFrame()

    d = df[[group_col, "Descricao", "Fornecedor", "Numero", DATE_COL, MONEY_COL]].copy()
    d = d.dropna(subset=[MONEY_COL])
    d[group_col] = d[group_col].fillna("")

    results = []
    for grp, part in d.groupby(group_col):
        if part.shape[0] < min_group_n:
            continue
        q1 = part[MONEY_COL].quantile(0.25)
        q3 = part[MONEY_COL].quantile(0.75)
        iqr = q3 - q1
        if iqr <= 0:
            continue
        upper = q3 + 1.5 * iqr
        flagged = part[part[MONEY_COL] > upper].sort_values(MONEY_COL, ascending=False)
        if not flagged.empty:
            flagged = flagged.assign(IQR_Upper=upper)
            results.append(flagged)

    if not results:
        return pd.DataFrame()

    out = pd.concat(results, ignore_index=True)
    out = out.sort_values(MONEY_COL, ascending=False).head(top_n)
    return out


# ----------------------------
# Orçamento
# ----------------------------

def _months_between(start_dt: pd.Timestamp, end_dt: pd.Timestamp) -> List[str]:
    if pd.isna(start_dt) or pd.isna(end_dt):
        return []
    if end_dt < start_dt:
        return []
    pr = pd.period_range(start_dt.to_period("M"), end_dt.to_period("M"), freq="M")
    return [str(p) for p in pr]


def build_budget_from_sources() -> pd.DataFrame:
    """
    Constrói orçamento CONSOLIDADO por mês e centro de custo (código), a partir dos arquivos em config.py:

    - OPEX 2026.xlsx: expande INÍCIO/FIM em meses com VALOR MÊS e traz C. CUSTOS + ÁREA.
    - CAPEX *.xlsx: como não há centro de custo explícito nos modelos anexados, tratamos como CAPEX "GERAL"
      e distribuímos igualmente em 12 meses (2026-01..2026-12) para habilitar o comparativo mensal.
      (Se você tiver CAPEX por centro de custo, dá para evoluir depois.)

    Saída:
      Mes, C. CUSTOS, ÁREA, OPEX, CAPEX
    """
    frames = []

    # ----- OPEX -----
    if os.path.exists(BUDGET_OPEX_2026_PATH):
        o = pd.read_excel(BUDGET_OPEX_2026_PATH, engine="openpyxl")
        o = o.rename(columns={c: str(c).strip() for c in o.columns})

        # normaliza colunas esperadas
        for col in [BUDGET_CC_CODE_COL, BUDGET_AREA_COL]:
            if col not in o.columns:
                o[col] = ""

        if "VALOR MÊS" in o.columns:
            o["VALOR MÊS"] = pd.to_numeric(o["VALOR MÊS"], errors="coerce").fillna(0.0)
        else:
            o["VALOR MÊS"] = 0.0

        o["INÍCIO"] = pd.to_datetime(o.get("INÍCIO"), errors="coerce")
        o["FIM"] = pd.to_datetime(o.get("FIM"), errors="coerce")

        rows = []
        for _, r in o.iterrows():
            meses = _months_between(r.get("INÍCIO"), r.get("FIM"))
            val = float(r.get("VALOR MÊS") or 0.0)

            cc = str(r.get(BUDGET_CC_CODE_COL) or "").strip()
            area = str(r.get(BUDGET_AREA_COL) or "").strip()

            # Se não vier CC, joga em um bucket "SEM_CC" (para não perder)
            if cc == "":
                cc = "SEM_CC"
            if area == "":
                area = "Sem área"

            for m in meses:
                rows.append({
                    "Mes": m,
                    BUDGET_CC_CODE_COL: cc,
                    BUDGET_AREA_COL: area,
                    "OPEX": val,
                    "CAPEX": 0.0
                })

        if rows:
            frames.append(pd.DataFrame(rows))

    # ----- CAPEX (anual -> mensalizado) -----
    def _capex_total(path: str) -> float:
        if not os.path.exists(path):
            return 0.0
        try:
            df = pd.read_excel(path, sheet_name="UNIDADE", engine="openpyxl", header=2)
            val_col = df.columns[-2] if str(df.columns[-1]).lower().startswith("unnamed") else df.columns[-1]
            d = df.iloc[1:].copy()
            total = pd.to_numeric(d[val_col], errors="coerce").sum(skipna=True)
            return float(total or 0.0)
        except Exception:
            return 0.0

    capex_total = _capex_total(BUDGET_CAPEX_LOG_PATH) + _capex_total(BUDGET_CAPEX_STARLINK_PATH)
    if capex_total > 0:
        monthly = capex_total / 12.0
        cap_rows = [{
            "Mes": f"2026-{m:02d}",
            BUDGET_CC_CODE_COL: "CAPEX_GERAL",
            BUDGET_AREA_COL: "CAPEX (Sem CC nos arquivos)",
            "OPEX": 0.0,
            "CAPEX": monthly
        } for m in range(1, 13)]
        frames.append(pd.DataFrame(cap_rows))

    if not frames:
        return pd.DataFrame(columns=[BUDGET_MONTH_COL, BUDGET_CC_CODE_COL, BUDGET_AREA_COL, "OPEX", "CAPEX"])

    b = pd.concat(frames, ignore_index=True)
    b[BUDGET_MONTH_COL] = b[BUDGET_MONTH_COL].astype(str).str.slice(0, 7)
    b[BUDGET_CC_CODE_COL] = b[BUDGET_CC_CODE_COL].astype(str).str.strip()
    b[BUDGET_AREA_COL] = b[BUDGET_AREA_COL].astype(str).str.strip()

    for c in ["OPEX", "CAPEX"]:
        b[c] = pd.to_numeric(b[c], errors="coerce").fillna(0.0)

    b = b.groupby([BUDGET_MONTH_COL, BUDGET_CC_CODE_COL, BUDGET_AREA_COL], as_index=False)[["OPEX", "CAPEX"]].sum()
    b = b.sort_values([BUDGET_MONTH_COL, BUDGET_AREA_COL])
    return b


def ensure_budget_exists() -> pd.DataFrame:
    """
    Se budget.csv não existir, tenta construir a partir dos arquivos de orçamento (config.py) e salvar.
    """
    b = load_budget()
    if b.empty:
        b = build_budget_from_sources()
        if not b.empty:
            save_budget(b)
    return b

def load_budget() -> pd.DataFrame:
    """
    Carrega o orçamento consolidado (budget.csv).

    Esquema esperado:
      - Mes (YYYY-MM)
      - C. CUSTOS (código do centro de custo)
      - ÁREA (nome/área para rótulo)
      - OPEX
      - CAPEX
    """
    if not os.path.exists(BUDGET_PATH):
        return pd.DataFrame(columns=[BUDGET_MONTH_COL, BUDGET_CC_CODE_COL, BUDGET_AREA_COL, "OPEX", "CAPEX"])

    b = pd.read_csv(BUDGET_PATH, encoding="utf-8").copy()

    # Garante colunas mínimas (robustez)
    for c in [BUDGET_MONTH_COL, BUDGET_CC_CODE_COL, BUDGET_AREA_COL, "OPEX", "CAPEX"]:
        if c not in b.columns:
            b[c] = ""

    b[BUDGET_MONTH_COL] = b[BUDGET_MONTH_COL].astype(str).str.slice(0, 7)
    b[BUDGET_CC_CODE_COL] = b[BUDGET_CC_CODE_COL].astype(str).str.strip()
    b[BUDGET_AREA_COL] = b[BUDGET_AREA_COL].astype(str).str.strip()

    for c in ["OPEX", "CAPEX"]:
        b[c] = pd.to_numeric(b[c], errors="coerce").fillna(0.0)

    b = b.groupby([BUDGET_MONTH_COL, BUDGET_CC_CODE_COL, BUDGET_AREA_COL], as_index=False)[["OPEX", "CAPEX"]].sum()
    return b


def save_budget(df_budget: pd.DataFrame) -> None:
    os.makedirs(os.path.dirname(BUDGET_PATH), exist_ok=True)
    df_budget.to_csv(BUDGET_PATH, index=False, encoding="utf-8")


def budget_vs_actual(actual_df: pd.DataFrame) -> pd.DataFrame:
    """
    Tabela por mês com Realizado vs Orçado (OPEX/CAPEX), variação absoluta e percentual.

    Observação importante:
    - Se o realizado estiver vazio (por filtro de datas, por exemplo), ainda assim devolvemos
      uma tabela baseada no orçamento (com realizado = 0) para não quebrar a tela.
    """
    budget = load_budget()

    # Se não há realizado (filtros podem zerar), devolve orçamento com realizado = 0
    if actual_df is None or actual_df.empty:
        if budget.empty:
            return pd.DataFrame(columns=[
                "Mes","OPEX_real","OPEX_orc","OPEX_var","OPEX_var_pct",
                "CAPEX_real","CAPEX_orc","CAPEX_var","CAPEX_var_pct",
                "Total_real","Total_orc","Total_var","Total_var_pct"
            ])
        merged = budget.copy()
        merged = merged.rename(columns={"OPEX": "OPEX_orc", "CAPEX": "CAPEX_orc"})
        merged["OPEX_real"] = 0.0
        merged["CAPEX_real"] = 0.0
        for t in ["OPEX", "CAPEX"]:
            merged[f"{t}_var"] = merged[f"{t}_real"] - merged[f"{t}_orc"]
            merged[f"{t}_var_pct"] = np.where(
                merged[f"{t}_orc"] > 0,
                (merged[f"{t}_var"] / merged[f"{t}_orc"]) * 100.0,
                0.0
            )
        merged["Total_real"] = merged["OPEX_real"] + merged["CAPEX_real"]
        merged["Total_orc"] = merged["OPEX_orc"] + merged["CAPEX_orc"]
        merged["Total_var"] = merged["Total_real"] - merged["Total_orc"]
        merged["Total_var_pct"] = np.where(
            merged["Total_orc"] > 0,
            (merged["Total_var"] / merged["Total_orc"]) * 100.0,
            0.0
        )
        return merged.sort_values("Mes")

    actual = (
        actual_df.groupby(["Mes", "Tipo Orçamento"])[MONEY_COL]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={MONEY_COL: "Realizado"})
    )

    # Pivot para colunas OPEX/CAPEX
    actual_p = (
        actual.pivot_table(index="Mes", columns="Tipo Orçamento", values="Realizado", aggfunc="sum", fill_value=0.0)
        .reset_index()
    )

    # Em DF vazio, o reset_index pode criar "index" em vez de "Mes"
    if "Mes" not in actual_p.columns and "index" in actual_p.columns:
        actual_p = actual_p.rename(columns={"index": "Mes"})
    if "Mes" not in actual_p.columns:
        actual_p["Mes"] = pd.Series(dtype=str)

    # Garante colunas OPEX/CAPEX
    if "OPEX" not in actual_p.columns:
        actual_p["OPEX"] = 0.0
    if "CAPEX" not in actual_p.columns:
        actual_p["CAPEX"] = 0.0

    # Merge com orçamento (suffixes garantem nomes)
    merged = actual_p.merge(
        budget,
        left_on="Mes",
        right_on=BUDGET_MONTH_COL,
        how="left",
        suffixes=("_real", "_orc")
    )
    if BUDGET_MONTH_COL in merged.columns and BUDGET_MONTH_COL != "Mes":
        merged = merged.drop(columns=[BUDGET_MONTH_COL])

    # Renomeia realizado
    if "OPEX" in merged.columns:
        # Segurança: se por algum motivo veio sem suffix
        merged = merged.rename(columns={"OPEX": "OPEX_real"})
    if "CAPEX" in merged.columns:
        merged = merged.rename(columns={"CAPEX": "CAPEX_real"})

    # Se veio com suffix (mais comum), já será OPEX_real/CAPEX_real e OPEX_orc/CAPEX_orc
    if "OPEX_real" not in merged.columns and "OPEX_real" in merged.columns:
        pass

    # Orçado ausente -> 0
    for c in ["OPEX_orc", "CAPEX_orc"]:
        if c not in merged.columns:
            merged[c] = 0.0
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0.0)

    for c in ["OPEX_real", "CAPEX_real"]:
        if c not in merged.columns:
            merged[c] = 0.0
        merged[c] = pd.to_numeric(merged[c], errors="coerce").fillna(0.0)

    for t in ["OPEX", "CAPEX"]:
        merged[f"{t}_var"] = merged[f"{t}_real"] - merged[f"{t}_orc"]
        merged[f"{t}_var_pct"] = np.where(
            merged[f"{t}_orc"] > 0,
            (merged[f"{t}_var"] / merged[f"{t}_orc"]) * 100.0,
            np.where(merged[f"{t}_real"] > 0, np.inf, 0.0)
        )

    merged["Total_real"] = merged["OPEX_real"] + merged["CAPEX_real"]
    merged["Total_orc"] = merged["OPEX_orc"] + merged["CAPEX_orc"]
    merged["Total_var"] = merged["Total_real"] - merged["Total_orc"]
    merged["Total_var_pct"] = np.where(
        merged["Total_orc"] > 0,
        (merged["Total_var"] / merged["Total_orc"]) * 100.0,
        np.where(merged["Total_real"] > 0, np.inf, 0.0)
    )

    return merged.sort_values("Mes")



def budget_vs_actual_by_cc_code(actual_df: pd.DataFrame) -> pd.DataFrame:
    """
    Comparativo por Mês + Centro de Custo (código) para OPEX/CAPEX.
    - Realizado: usa colunas Mes, Centro Custo, Descr CC, Tipo Orçamento e Vlr.Total
    - Orçado: Mes, C. CUSTOS, ÁREA, OPEX, CAPEX

    CAPEX nos arquivos anexados não tem CC -> cai em CAPEX_GERAL, então aparecerá como uma linha separada.
    """
    budget = load_budget()

    def _norm_cc(x):
        """ Normaliza código de centro de custo:
        - se vier float 1234.0 -> "1234"
        - remove espaços
        - mantém zeros à esquerda se vier como string """
        
        if pd.isna(x):
            return ""
        s = str(x).strip()
        # trata número vindo como "1234.0"
        if s.endswith(".0"):
            s = s[:-2]
        # trata casos "1234,0" (raro)
        if s.endswith(",0"):
            s = s[:-2]
        return s


    # Realizado agregado por Mes + Centro Custo + Tipo
    if actual_df is None or actual_df.empty:
        # devolve orçamento com realizado = 0 (para não quebrar a tela)
        if budget.empty:
            return pd.DataFrame(columns=[
                "Mes", "Centro Custo", "Centro_nome",
                "OPEX_real", "OPEX_orc", "OPEX_var", "OPEX_var_pct",
                "CAPEX_real", "CAPEX_orc", "CAPEX_var", "CAPEX_var_pct",
                "Total_real", "Total_orc", "Total_var", "Total_var_pct"
            ])
        b = budget.rename(columns={BUDGET_CC_CODE_COL: "Centro Custo", BUDGET_AREA_COL: "Centro_nome", "OPEX": "OPEX_orc", "CAPEX": "CAPEX_orc"})
        b["OPEX_real"] = 0.0
        b["CAPEX_real"] = 0.0
        for t in ["OPEX", "CAPEX"]:
            b[f"{t}_var"] = b[f"{t}_real"] - b[f"{t}_orc"]
            b[f"{t}_var_pct"] = np.where(b[f"{t}_orc"] > 0, (b[f"{t}_var"] / b[f"{t}_orc"]) * 100.0, 0.0)
        b["Total_real"] = 0.0
        b["Total_orc"] = b["OPEX_orc"] + b["CAPEX_orc"]
        b["Total_var"] = -b["Total_orc"]
        b["Total_var_pct"] = np.where(b["Total_orc"] > 0, (b["Total_var"] / b["Total_orc"]) * 100.0, 0.0)
        return b.sort_values(["Mes", "Centro_nome"])

    act = (
        actual_df.groupby(["Mes", "Centro Custo", "Tipo Orçamento"])[MONEY_COL]
        .sum(min_count=1)
        .reset_index()
        .rename(columns={MONEY_COL: "Realizado"})
    )

    act_p = act.pivot_table(index=["Mes", "Centro Custo"], columns="Tipo Orçamento", values="Realizado", aggfunc="sum", fill_value=0.0).reset_index()
    act_p["Centro Custo"] = act_p["Centro Custo"].apply(_norm_cc)
    if "OPEX" not in act_p.columns:
        act_p["OPEX"] = 0.0
    if "CAPEX" not in act_p.columns:
        act_p["CAPEX"] = 0.0
    act_p = act_p.rename(columns={"OPEX": "OPEX_real", "CAPEX": "CAPEX_real"})

    # Nome do CC no realizado (mais frequente)
    if "Descr CC" in actual_df.columns:
        cc_name = (
            actual_df.dropna(subset=["Centro Custo"])
            .groupby("Centro Custo")["Descr CC"]
            .agg(lambda s: s.value_counts().index[0] if len(s) else "")
            .reset_index()
            .rename(columns={"Descr CC": "Descr_CC_real"})
        )
        act_p = act_p.merge(cc_name, on="Centro Custo", how="left")
    else:
        act_p["Descr_CC_real"] = ""

    b = budget.rename(columns={BUDGET_CC_CODE_COL: "Centro Custo", BUDGET_AREA_COL: "Area_budget", "OPEX": "OPEX_orc", "CAPEX": "CAPEX_orc"})
    b["Centro Custo"] = b["Centro Custo"].apply(_norm_cc)
    b = b[["Mes", "Centro Custo", "Area_budget", "OPEX_orc", "CAPEX_orc"]]

    merged = act_p.merge(b, on=["Mes", "Centro Custo"], how="left")
    merged["OPEX_orc"] = pd.to_numeric(merged["OPEX_orc"], errors="coerce").fillna(0.0)
    merged["CAPEX_orc"] = pd.to_numeric(merged["CAPEX_orc"], errors="coerce").fillna(0.0)
    merged["Area_budget"] = merged["Area_budget"].fillna("")

    # Nome final do centro
    merged["Centro_nome"] = np.where(merged["Area_budget"].astype(str).str.strip() != "", merged["Area_budget"], merged["Descr_CC_real"].fillna(""))

    for t in ["OPEX", "CAPEX"]:
        merged[f"{t}_var"] = merged[f"{t}_real"] - merged[f"{t}_orc"]
        merged[f"{t}_var_pct"] = np.where(
            merged[f"{t}_orc"] > 0,
            (merged[f"{t}_var"] / merged[f"{t}_orc"]) * 100.0,
            np.where(merged[f"{t}_real"] > 0, np.inf, 0.0)
        )

    merged["Total_real"] = merged["OPEX_real"] + merged["CAPEX_real"]
    merged["Total_orc"] = merged["OPEX_orc"] + merged["CAPEX_orc"]
    merged["Total_var"] = merged["Total_real"] - merged["Total_orc"]
    merged["Total_var_pct"] = np.where(
        merged["Total_orc"] > 0,
        (merged["Total_var"] / merged["Total_orc"]) * 100.0,
        np.where(merged["Total_real"] > 0, np.inf, 0.0)
    )

    return merged.sort_values(["Mes", "Centro_nome"])


def budget_cc_options(actual_df: pd.DataFrame) -> list[dict]:
    """
    Retorna lista de opções de CC para dropdown:
    [{code: '123', name: 'ÁREA X'}, ...]
    Combina realizado (Centro Custo/Descr CC) com orçamento (C. CUSTOS/ÁREA).
    """
    # realizado
    act = actual_df.copy()
    if "Centro Custo" not in act.columns:
        return []

    act_cc = (
        act.dropna(subset=["Centro Custo"])
        .assign(cc=lambda d: d["Centro Custo"].astype(str).str.strip().str.replace(".0", "", regex=False),
                name=lambda d: d.get("Descr CC", "").astype(str))
        .groupby("cc")["name"]
        .agg(lambda s: s.value_counts().index[0] if len(s) else "")
        .reset_index()
        .rename(columns={"cc": "code", "name": "name"})
    )

    # orçamento (se existir)
    b = load_budget()
    if not b.empty and "C. CUSTOS" in b.columns:
        b_cc = (
            b.assign(code=lambda d: d["C. CUSTOS"].astype(str).str.strip().str.replace(".0", "", regex=False),
                     name=lambda d: d.get("ÁREA", "").astype(str))
            .groupby("code")["name"]
            .agg(lambda s: s.value_counts().index[0] if len(s) else "")
            .reset_index()
        )
        merged = act_cc.merge(b_cc, on="code", how="outer", suffixes=("_act", "_bud"))
        merged["name"] = merged["name_bud"].fillna("").where(merged["name_bud"].fillna("") != "", merged["name_act"].fillna(""))
        out = merged[["code", "name"]]
    else:
        out = act_cc[["code", "name"]]

    out = out.fillna("")
    out = out.sort_values(["name", "code"])
    return out.to_dict(orient="records")


# ----------------------------
# Opções para filtros
# ----------------------------

def filter_options(df: pd.DataFrame) -> Dict[str, List[str]]:
    def _vals(col):
        if col not in df.columns:
            return []
        vals = sorted([v for v in df[col].dropna().astype(str).unique().tolist() if v.strip() != ""])
        return vals

    return {
        "tipo_orc": ["ALL", "OPEX", "CAPEX", "N/I"],
        "unidade2": ["ALL"] + _vals("Unidade2"),
        "area": ["ALL"] + _vals("Área"),
    }