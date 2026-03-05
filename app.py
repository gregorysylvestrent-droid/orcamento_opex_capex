import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

import pandas as pd
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go


from config import SECRET_KEY, DEFAULT_EXCEL_PATH, DEFAULT_SHEET_NAME, DATA_DIR
from services.data import (
    load_data, apply_filters, kpis, breakdown, timeseries, share_opex_capex,
    outliers_iqr, filter_options, load_budget, save_budget, budget_vs_actual,
    ensure_budget_exists, build_budget_from_sources, budget_vs_actual_by_cc_code,
    budget_cc_options
)

pio.templates.default = "plotly_white"


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

    # Fonte atual (pode mudar via upload)
    app.config["EXCEL_PATH"] = DEFAULT_EXCEL_PATH
    app.config["SHEET_NAME"] = DEFAULT_SHEET_NAME

    def get_df():
        return load_data(app.config["EXCEL_PATH"], app.config["SHEET_NAME"])

    def get_filtered_df(df):
        return apply_filters(
            df,
            start=request.args.get("start") or None,
            end=request.args.get("end") or None,
            tipo_orc=request.args.get("tipo_orc") or None,
            unidade2=request.args.get("unidade2") or None,
            area=request.args.get("area") or None,
        )

    def common_context(df_filtered):
        opts = filter_options(get_df())
        ctx = {
            "opts": opts,
            "filters": {
                "start": request.args.get("start", ""),
                "end": request.args.get("end", ""),
                "tipo_orc": request.args.get("tipo_orc", "ALL"),
                "unidade2": request.args.get("unidade2", "ALL"),
                "area": request.args.get("area", "ALL"),
            },
            "source": {
                "excel_path": app.config["EXCEL_PATH"],
                "sheet": app.config["SHEET_NAME"],
                "rows": int(df_filtered.shape[0]),
            }
        }
        return ctx

    @app.route("/")
    def home():
        return redirect(url_for("dashboard"))

    @app.route("/dashboard")
    def dashboard():
        df = get_df()
        f = get_filtered_df(df)
        ensure_budget_exists()

        k = kpis(f)
        share = share_opex_capex(f)
        ts = timeseries(f)
        top_fornec = breakdown(f, "Fornecedor", top_n=10)
        top_cc = breakdown(f, "Descr CC", top_n=10)
        top_cta = breakdown(f, "Cta. Descrição", top_n=10)
        top_grupo = breakdown(f, "Grupo", top_n=10)

        # Gráficos
        fig_share = px.pie(share, names="Tipo Orçamento", values="Valor", hole=0.55, title="OPEX vs CAPEX (participação)")
        fig_ts = px.area(ts, x="Mes", y="Valor", color="Tipo Orçamento", markers=True, title="Evolução mensal (Realizado)")
        fig_fornec = px.bar(top_fornec, x="Fornecedor", y="Valor", title="Top 10 Fornecedores (R$)", text_auto=".2s")
        fig_cc = px.bar(top_cc, x="Descr CC", y="Valor", title="Top 10 Centros de Custo (R$)", text_auto=".2s")
        fig_cta = px.bar(top_cta, x="Cta. Descrição", y="Valor", title="Top 10 Contas/Categorias (R$)", text_auto=".2s")
        fig_grupo = px.treemap(top_grupo, path=["Grupo"], values="Valor", title="Distribuição por Grupo (treemap)")

        # Outliers
        out = outliers_iqr(f, group_col="Cta. Descrição", min_group_n=20, top_n=30)
        out_records = []
        if not out.empty:
            out_records = out.assign(
                **{"Data Emissao": out["Data Emissao"].dt.strftime("%Y-%m-%d")}
            ).to_dict(orient="records")

        ctx = common_context(f)
        ctx.update({
            "kpi": k,
            "fig_share": fig_share.to_json(),
            "fig_ts": fig_ts.to_json(),
            "fig_fornec": fig_fornec.to_json(),
            "fig_cc": fig_cc.to_json(),
            "fig_cta": fig_cta.to_json(),
            "fig_grupo": fig_grupo.to_json(),
            "outliers": out_records,
        })
        return render_template("dashboard.html", **ctx)

    @app.route("/details")
    def details():
        df = get_df()
        f = get_filtered_df(df)

        # Seleciona colunas mais úteis (mantém robusto se alguma faltar)
        cols = [c for c in [
            "Numero", "Data Emissao", "Fornecedor", "Descricao", "Quantidade", "Unidade",
            "Vlr.Total", "Vl. Desconto", "Tipo Orçamento", "Grupo", "Cta. Descrição",
            "Descr CC", "PLACA VEICUL", "Status do ME", "Origem", "Unidade2", "Área"
        ] if c in f.columns]

        view = f[cols].copy()
        if "Data Emissao" in view.columns:
            view["Data Emissao"] = view["Data Emissao"].dt.strftime("%Y-%m-%d")

        records = view.fillna("").to_dict(orient="records")

        ctx = common_context(f)
        ctx.update({"rows": records, "cols": cols})
        return render_template("details.html", **ctx)
    @app.route("/budget", methods=["GET", "POST"])
    def budget():
        df = get_df()
        f = get_filtered_df(df)
        ensure_budget_exists()

        if request.method == "POST":
            # Lançamento manual por mês + centro de custo (código) + área (nome)
            mes = (request.form.get("mes") or "").strip()[:7]
            cc = (request.form.get("cc") or "").strip()
            area = (request.form.get("area") or "").strip()
            opex = request.form.get("opex") or "0"
            capex = request.form.get("capex") or "0"

            if not cc:
                cc = "SEM_CC"
            if not area:
                area = "Sem área"

            try:
                opex_v = float(str(opex).replace(".", "").replace(",", "."))
                capex_v = float(str(capex).replace(".", "").replace(",", "."))
            except Exception:
                flash("Valores inválidos. Use números.", "danger")
                return redirect(url_for("budget", **filters_from_request()))

            b = load_budget()

            # Atualiza/insere (Mes + CC + Área)
            mask = (b["Mes"] == mes) & (b["C. CUSTOS"].astype(str) == str(cc)) & (b["ÁREA"].astype(str) == str(area))
            if mask.any():
                b.loc[mask, "OPEX"] = opex_v
                b.loc[mask, "CAPEX"] = capex_v
            else:
                b = pd.concat([b, pd.DataFrame([{"Mes": mes, "C. CUSTOS": cc, "ÁREA": area, "OPEX": opex_v, "CAPEX": capex_v}])], ignore_index=True)

            b = b.sort_values(["Mes", "ÁREA"])
            save_budget(b)
            flash("Orçamento salvo.", "success")
            return redirect(url_for("budget", **filters_from_request()))

        # Comparativo por CC (gerencial)
        comp_cc = budget_vs_actual_by_cc_code(f).replace([float("inf")], None)
        comp_cc_records = comp_cc.fillna("").to_dict(orient="records")

        # KPIs executivos (somatórios)
        total_real = float(comp_cc["Total_real"].sum()) if not comp_cc.empty else 0.0
        total_orc = float(comp_cc["Total_orc"].sum()) if not comp_cc.empty else 0.0
        total_var = total_real - total_orc
        total_var_pct = (total_var / total_orc * 100.0) if total_orc else (float("inf") if total_real else 0.0)

        # Ranking: piores desvios (R$) por centro
        rank = (
            comp_cc.groupby("Centro_nome")["Total_var"].sum()
            .sort_values(ascending=False)
            .head(10)
            .reset_index()
            .rename(columns={"Centro_nome": "Centro", "Total_var": "Desvio"})
        )

        # Heatmap: Top 20 centros por gasto (desvio % médio)
        top_centros = (
            comp_cc.groupby("Centro_nome")["Total_real"].sum()
            .sort_values(ascending=False)
            .head(20)
            .index.tolist()
        )
        hm = comp_cc[comp_cc["Centro_nome"].isin(top_centros)].copy()
        pivot = hm.pivot_table(index="Centro_nome", columns="Mes", values="Total_var_pct", aggfunc="mean").fillna(0.0)

        fig_hm = px.imshow(pivot, aspect="auto", title="Heatmap: Desvio % (Top 20 centros por gasto)")

        ctx = common_context(f)
        ctx.update({
            "budget_rows": load_budget().sort_values(["Mes", "ÁREA"]).to_dict(orient="records"),
            "comp_cc_rows": comp_cc_records,
            "kpi_budget": {"real": total_real, "orc": total_orc, "var": total_var, "var_pct": total_var_pct},
            "rank_rows": rank.fillna("").to_dict(orient="records"),
            "fig_hm": fig_hm.to_json(),
        })
        return render_template("budget.html", **ctx)


    
    @app.route("/budget/import", methods=["POST"])
    def budget_import():
        # Rebuild budget.csv from the source files configured in config.py
        b = build_budget_from_sources()
        if b.empty:
            flash("Não foi possível gerar orçamento a partir dos arquivos. Coloque os arquivos na pasta /data ou use o lançamento manual.", "warning")
        else:
            save_budget(b)
            flash("Orçamento importado/atualizado a partir dos arquivos em /data.", "success")
        return redirect(url_for("budget"))


    @app.route("/upload", methods=["GET", "POST"])
    def upload():
        if request.method == "POST":
            file = request.files.get("file")
            sheet = (request.form.get("sheet") or DEFAULT_SHEET_NAME).strip() or DEFAULT_SHEET_NAME

            if not file or file.filename.strip() == "":
                flash("Selecione um arquivo.", "danger")
                return redirect(url_for("upload"))

            filename = "uploaded.xlsx"
            save_path = os.path.join(DATA_DIR, filename)
            file.save(save_path)

            app.config["EXCEL_PATH"] = save_path
            app.config["SHEET_NAME"] = sheet

            flash(f"Arquivo carregado! Fonte atual: {save_path} | Aba: {sheet}", "success")
            return redirect(url_for("dashboard"))

        df = get_df()
        f = get_filtered_df(df)
        ctx = common_context(f)
        ctx.update({"source": {"excel_path": app.config["EXCEL_PATH"], "sheet": app.config["SHEET_NAME"], "rows": int(f.shape[0])}})
        return render_template("upload.html", **ctx)

    @app.route("/api/summary")
    def api_summary():
        df = get_df()
        f = get_filtered_df(df)

        payload = {
            "kpi": kpis(f),
            "share": share_opex_capex(f).to_dict(orient="records"),
            "timeseries": timeseries(f).to_dict(orient="records"),
            "top_fornec": breakdown(f, "Fornecedor", 10).to_dict(orient="records"),
            "top_cc": breakdown(f, "Descr CC", 10).to_dict(orient="records"),
            "top_cta": breakdown(f, "Cta. Descrição", 10).to_dict(orient="records"),
        }
        return jsonify(payload)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
