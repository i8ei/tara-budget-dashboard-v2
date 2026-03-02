"""
太良町立病院事業会計 予算ダッシュボード（統合ビュー）
dashboard-v2 のサイドバーから呼び出される。
"""

import os
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from common import BASE_DIR

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "hospital_budget.db")
FY_ORDER = ["R4", "R5", "R6", "R7", "R8"]
FY_LABELS = {"R4": "令和4年度", "R5": "令和5年度", "R6": "令和6年度", "R7": "令和7年度", "R8": "令和8年度"}

# 事業名マッピング（款番号→短縮名）
BIZ_NAMES = {
    1: "病院本体",
    2: "訪問看護ST",
    3: "居宅介護支援",
    4: "通所リハ",
    5: "訪問リハ",
}

# IBM Colorblind Safe パレット（色覚多様性対応）
COLORS = ["#648FFF", "#785EF0", "#DC267F", "#FE6100", "#FFB000"]


# ──────────────────────────────────────────────
# DB接続・データ読み込み
# ──────────────────────────────────────────────
@st.cache_data
def _load_hospital_data():
    conn = sqlite3.connect(DB_PATH)
    metrics = pd.read_sql("SELECT * FROM business_metrics", conn)
    items = pd.read_sql("SELECT * FROM budget_items", conn)
    cap_summary = pd.read_sql("SELECT * FROM capital_summary", conn)
    conn.close()

    for df in [metrics, items, cap_summary]:
        df["fiscal_year"] = pd.Categorical(df["fiscal_year"], categories=FY_ORDER, ordered=True)
    metrics = metrics.sort_values("fiscal_year")
    cap_summary = cap_summary.sort_values("fiscal_year")

    return metrics, items, cap_summary


def _fy_label(fy):
    return FY_LABELS.get(fy, fy)


def _fy_labels_list():
    return [_fy_label(fy) for fy in FY_ORDER]


# ──────────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────────
def _sum_by_fy(items, section):
    mask = (items["section"] == section) & (items["level"] == "款")
    return items[mask].groupby("fiscal_year", observed=True)["amount"].sum().reset_index()


# ──────────────────────────────────────────────
# メイン render 関数
# ──────────────────────────────────────────────
def render():
    st.header("太良町立病院事業会計 予算ダッシュボード")
    st.caption("令和4年度 - 令和8年度（5年間）/ 単位：千円")

    metrics, items, cap_summary = _load_hospital_data()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "概況",
        "経営指標",
        "事業別収支",
        "費用構造",
        "資本的収支",
        "一般会計依存度",
    ])

    # ==============================================================
    # タブ1: 概況
    # ==============================================================
    with tab1:
        st.subheader("経営概況（5年間推移）")

        rev_total = _sum_by_fy(items, "収益的収入")
        rev_total["label"] = "収益的収入"
        exp_total = _sum_by_fy(items, "収益的支出")
        exp_total["label"] = "収益的支出"
        re_df = pd.concat([rev_total, exp_total])
        re_df["fy_label"] = re_df["fiscal_year"].map(_fy_label)

        fig1 = px.line(
            re_df, x="fy_label", y="amount", color="label",
            markers=True,
            title="収益的収入・支出の推移",
            labels={"fy_label": "年度", "amount": "金額（千円）", "label": "区分"},
        )
        fig1.update_layout(hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

        # --- 主要経営指標 ---
        st.subheader("主要経営指標の推移")

        indicator_rows = []
        for _, row in metrics.iterrows():
            fy = row["fiscal_year"]
            med_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["level"] == "項")
            ]["amount"].sum()
            med_exp = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["level"] == "項")
            ]["amount"].sum()
            bed_util = row["daily_avg_inpatients"] / row["beds"] * 100 if row["beds"] > 0 else 0
            total_salary = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["level"] == "目") & (items["moku_name"] == "給与費")
            ]["amount"].sum()
            total_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") & (items["level"] == "款")
            ]["amount"].sum()
            personnel_ratio = total_salary / total_rev * 100 if total_rev > 0 else 0
            med_ratio = med_rev / med_exp * 100 if med_exp > 0 else 0

            indicator_rows.append({
                "年度": _fy_label(fy),
                "医業収支比率(%)": round(med_ratio, 1),
                "病床利用率(%)": round(bed_util, 1),
                "人件費比率(%)": round(personnel_ratio, 1),
            })

        ind_df = pd.DataFrame(indicator_rows)

        col1, col2, col3 = st.columns(3)
        with col1:
            fig_m = px.line(ind_df, x="年度", y="医業収支比率(%)", markers=True, title="医業収支比率")
            fig_m.add_hline(y=100, line_dash="dash", line_color="red", annotation_text="100%ライン")
            st.plotly_chart(fig_m, use_container_width=True)
        with col2:
            fig_b = px.line(ind_df, x="年度", y="病床利用率(%)", markers=True, title="病床利用率（60床）")
            st.plotly_chart(fig_b, use_container_width=True)
        with col3:
            fig_p = px.line(ind_df, x="年度", y="人件費比率(%)", markers=True, title="人件費比率")
            st.plotly_chart(fig_p, use_container_width=True)

        st.dataframe(ind_df.set_index("年度"), use_container_width=True)

        # --- 業務予定量 ---
        st.subheader("業務予定量の推移")
        met_disp = metrics.copy()
        met_disp["年度"] = met_disp["fiscal_year"].map(_fy_label)
        met_disp = met_disp.rename(columns={
            "beds": "病床数",
            "annual_inpatients": "年間入院患者(人)",
            "daily_avg_inpatients": "1日平均入院(人)",
            "annual_outpatients": "年間外来患者(人)",
            "daily_avg_outpatients": "1日平均外来(人)",
            "staff_salary": "職員給与費(千円)",
            "general_account_subsidy": "一般会計繰出金(千円)",
        })
        st.dataframe(
            met_disp[["年度", "病床数", "年間入院患者(人)", "1日平均入院(人)",
                      "年間外来患者(人)", "1日平均外来(人)", "職員給与費(千円)", "一般会計繰出金(千円)"]].set_index("年度"),
            use_container_width=True,
        )

    # ==============================================================
    # タブ2: 経営指標
    # ==============================================================
    with tab2:
        st.subheader("経営指標（予算ベース）")
        st.caption("予算書から算出可能な主要経営指標を一覧表示します")

        POPULATION = 8_000

        ind2_rows = []
        for _, row in metrics.iterrows():
            fy = row["fiscal_year"]
            beds = row["beds"]
            annual_inp = row["annual_inpatients"]
            daily_inp = row["daily_avg_inpatients"]
            annual_out = row["annual_outpatients"]
            daily_out = row["daily_avg_outpatients"]
            ga_subsidy = row["general_account_subsidy"]

            med_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["level"] == "項")
            ]["amount"].sum()
            med_exp = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["level"] == "項")
            ]["amount"].sum()
            inp_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["moku_no"] == 1) &
                (items["level"] == "目")
            ]["amount"].sum()
            out_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) & (items["moku_no"] == 2) &
                (items["level"] == "目")
            ]["amount"].sum()
            total_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") & (items["level"] == "款")
            ]["amount"].sum()
            total_exp = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["level"] == "款") & (items["kwan_no"] != 6)
            ]["amount"].sum()
            salary_hosp = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) &
                (items["level"] == "目") & (items["moku_name"] == "給与費")
            ]["amount"].sum()
            salary_all = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["level"] == "目") & (items["moku_name"] == "給与費")
            ]["amount"].sum()
            material = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) &
                (items["level"] == "目") & (items["moku_name"] == "材料費")
            ]["amount"].sum()
            keihi = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) &
                (items["level"] == "目") & (items["moku_name"] == "経費")
            ]["amount"].sum()
            depreciation = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 1) &
                (items["level"] == "目") & (items["moku_name"] == "減価償却費")
            ]["amount"].sum()
            non_med_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 2) & (items["level"] == "項")
            ]["amount"].sum()
            ga_subsidy_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 2) & (items["moku_no"] == 1) &
                (items["level"] == "目")
            ]["amount"].sum()
            interest = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 2) &
                (items["level"] == "目") & (items["moku_name"].str.contains("支払利息", na=False))
            ]["amount"].sum()
            bond_repay = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的支出") &
                (items["level"] == "款") & (items["kwan_name"] == "企業債償還金")
            ]["amount"].sum()

            med_ratio = med_rev / med_exp * 100 if med_exp > 0 else 0
            mod_med_ratio = (med_rev + ga_subsidy_rev) / med_exp * 100 if med_exp > 0 else 0
            bed_util = daily_inp / beds * 100 if beds > 0 else 0
            inp_unit = inp_rev / annual_inp * 1000 if annual_inp > 0 else 0
            out_unit = out_rev / annual_out * 1000 if annual_out > 0 else 0
            salary_ratio_hosp = salary_hosp / med_rev * 100 if med_rev > 0 else 0
            salary_ratio_all = salary_all / total_rev * 100 if total_rev > 0 else 0
            material_ratio = material / med_rev * 100 if med_rev > 0 else 0
            keihi_ratio = keihi / med_rev * 100 if med_rev > 0 else 0
            depreciation_ratio = depreciation / med_rev * 100 if med_rev > 0 else 0
            dep_ratio = ga_subsidy / total_rev * 100 if total_rev > 0 else 0
            per_capita = ga_subsidy / POPULATION * 1000
            per_bed = ga_subsidy / beds if beds > 0 else 0
            ordinary_ratio = total_rev / total_exp * 100 if total_exp > 0 else 0
            care_rev = total_rev - items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["level"] == "款")
            ]["amount"].sum()
            hosp_total = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["level"] == "款")
            ]["amount"].sum()

            ind2_rows.append({
                "年度": _fy_label(fy),
                "fiscal_year": fy,
                "医業収支比率": round(med_ratio, 1),
                "修正医業収支比率": round(mod_med_ratio, 1),
                "経常収支比率": round(ordinary_ratio, 1),
                "病床利用率": round(bed_util, 1),
                "入院単価(円/日)": round(inp_unit),
                "外来単価(円/日)": round(out_unit),
                "給与費比率(病院)": round(salary_ratio_hosp, 1),
                "給与費比率(全体)": round(salary_ratio_all, 1),
                "材料費率": round(material_ratio, 1),
                "経費率": round(keihi_ratio, 1),
                "減価償却費率": round(depreciation_ratio, 1),
                "繰出依存度": round(dep_ratio, 1),
                "住民1人当たり繰出(円)": round(per_capita),
                "1床当たり繰出(千円)": round(per_bed),
                "支払利息": interest,
                "企業債償還金": bond_repay,
                "入院収益": inp_rev,
                "外来収益": out_rev,
                "介護等収益": care_rev,
                "病院事業収益": hosp_total,
                "医業収益": med_rev,
                "医業費用": med_exp,
                "他会計補助金": ga_subsidy_rev,
            })

        ind2_df = pd.DataFrame(ind2_rows)

        # 収益性指標
        st.subheader("収益性指標")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            fig_med = go.Figure()
            fig_med.add_trace(go.Scatter(x=ind2_df["年度"], y=ind2_df["医業収支比率"], name="医業収支比率", mode="lines+markers"))
            fig_med.add_trace(go.Scatter(x=ind2_df["年度"], y=ind2_df["修正医業収支比率"], name="修正医業収支比率", mode="lines+markers", line=dict(dash="dash")))
            fig_med.add_hline(y=100, line_dash="dot", line_color="red", annotation_text="100%")
            fig_med.update_layout(title="医業収支比率の推移", yaxis_title="%", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_med, use_container_width=True)
        with col_b:
            fig_ord = px.line(ind2_df, x="年度", y="経常収支比率", markers=True, title="経常収支比率")
            fig_ord.add_hline(y=100, line_dash="dot", line_color="red", annotation_text="100%")
            st.plotly_chart(fig_ord, use_container_width=True)
        with col_c:
            fig_bed = px.line(ind2_df, x="年度", y="病床利用率", markers=True, title="病床利用率")
            fig_bed.add_hline(y=70, line_dash="dot", line_color="orange", annotation_text="70%（健全ライン）")
            st.plotly_chart(fig_bed, use_container_width=True)

        # 患者単価
        st.subheader("患者単価の推移")
        col_d, col_e = st.columns(2)
        with col_d:
            fig_inp_u = px.bar(ind2_df, x="年度", y="入院単価(円/日)", title="入院患者1人1日当たり収益", text_auto=True)
            fig_inp_u.update_traces(texttemplate="%{y:,.0f}円")
            st.plotly_chart(fig_inp_u, use_container_width=True)
        with col_e:
            fig_out_u = px.bar(ind2_df, x="年度", y="外来単価(円/日)", title="外来患者1人1日当たり収益", text_auto=True)
            fig_out_u.update_traces(texttemplate="%{y:,.0f}円")
            st.plotly_chart(fig_out_u, use_container_width=True)

        # 費用構造比率
        st.subheader("費用構造比率（対医業収益）")
        col_f, col_g = st.columns(2)
        with col_f:
            fig_cost_ratio = go.Figure()
            for col_name, label in [("給与費比率(病院)", "給与費"), ("材料費率", "材料費"), ("経費率", "経費"), ("減価償却費率", "減価償却費")]:
                fig_cost_ratio.add_trace(go.Scatter(x=ind2_df["年度"], y=ind2_df[col_name], name=label, mode="lines+markers"))
            fig_cost_ratio.update_layout(title="費用構造比率の推移", yaxis_title="%", legend=dict(orientation="h", y=-0.2))
            st.plotly_chart(fig_cost_ratio, use_container_width=True)
        with col_g:
            fig_sal = go.Figure()
            fig_sal.add_trace(go.Bar(name="病院本体", x=ind2_df["年度"], y=ind2_df["給与費比率(病院)"], marker_color="#648FFF"))
            fig_sal.add_trace(go.Bar(name="全事業", x=ind2_df["年度"], y=ind2_df["給与費比率(全体)"], marker_color="#FFB000"))
            fig_sal.add_hline(y=55, line_dash="dot", line_color="red", annotation_text="目安55%")
            fig_sal.update_layout(title="給与費比率の比較", barmode="group", yaxis_title="%")
            st.plotly_chart(fig_sal, use_container_width=True)

        # 一般会計負担の深掘り
        st.subheader("一般会計負担の深掘り")
        col_h, col_i = st.columns(2)
        with col_h:
            fig_pc = px.bar(ind2_df, x="年度", y="住民1人当たり繰出(円)", title="住民1人当たり繰出金", text_auto=True)
            fig_pc.update_traces(texttemplate="%{y:,.0f}円")
            st.plotly_chart(fig_pc, use_container_width=True)
        with col_i:
            fig_pb = px.bar(ind2_df, x="年度", y="1床当たり繰出(千円)", title="1床当たり繰出金", text_auto=True)
            fig_pb.update_traces(texttemplate="%{y:,.0f}千円")
            st.plotly_chart(fig_pb, use_container_width=True)

        # 企業債・支払利息
        st.subheader("企業債負担の推移")
        col_j, col_k = st.columns(2)
        with col_j:
            fig_int = px.bar(ind2_df, x="年度", y="支払利息", title="支払利息の推移", text_auto=True)
            fig_int.update_traces(texttemplate="%{y:,.0f}")
            fig_int.update_layout(yaxis_title="金額（千円）")
            st.plotly_chart(fig_int, use_container_width=True)
        with col_k:
            fig_bond = px.bar(ind2_df, x="年度", y="企業債償還金", title="企業債償還金の推移", text_auto=True)
            fig_bond.update_traces(texttemplate="%{y:,.0f}")
            fig_bond.update_layout(yaxis_title="金額（千円）")
            st.plotly_chart(fig_bond, use_container_width=True)

        # 収益構造分析
        st.subheader("収益構造分析")
        rev_struct = []
        for _, row2 in ind2_df.iterrows():
            rev_struct.append({"年度": row2["年度"], "区分": "入院収益", "金額": row2["入院収益"]})
            rev_struct.append({"年度": row2["年度"], "区分": "外来収益", "金額": row2["外来収益"]})
            rev_struct.append({"年度": row2["年度"], "区分": "介護等事業", "金額": row2["介護等収益"]})
            rev_struct.append({"年度": row2["年度"], "区分": "他会計補助金", "金額": row2["他会計補助金"]})
        rev_struct_df = pd.DataFrame(rev_struct)
        fig_rev = px.bar(rev_struct_df, x="年度", y="金額", color="区分", title="収益構成の推移")
        fig_rev.update_layout(barmode="stack", yaxis_title="金額（千円）")
        st.plotly_chart(fig_rev, use_container_width=True)

        # 指標一覧テーブル
        st.subheader("経営指標一覧")
        display_cols = [
            "年度", "医業収支比率", "修正医業収支比率", "経常収支比率", "病床利用率",
            "入院単価(円/日)", "外来単価(円/日)",
            "給与費比率(病院)", "給与費比率(全体)", "材料費率", "経費率", "減価償却費率",
            "繰出依存度", "住民1人当たり繰出(円)", "1床当たり繰出(千円)",
        ]
        disp_df = ind2_df[display_cols].set_index("年度")
        fmt = {}
        for c in disp_df.columns:
            if "円" in c:
                fmt[c] = "{:,.0f}"
            elif "千円" in c:
                fmt[c] = "{:,.0f}"
            else:
                fmt[c] = "{:.1f}"
        st.dataframe(disp_df.style.format(fmt), use_container_width=True)

    # ==============================================================
    # タブ3: 事業別収支
    # ==============================================================
    with tab3:
        st.subheader("事業別収支比較")

        biz_data = []
        for fy in FY_ORDER:
            for kwan_no, biz_name in BIZ_NAMES.items():
                rev = items[
                    (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                    (items["kwan_no"] == kwan_no) & (items["level"] == "款")
                ]["amount"].sum()
                exp = items[
                    (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                    (items["kwan_no"] == kwan_no) & (items["level"] == "款")
                ]["amount"].sum()
                biz_data.append({
                    "fiscal_year": fy,
                    "年度": _fy_label(fy),
                    "事業": biz_name,
                    "収益": rev,
                    "費用": exp,
                    "損益": rev - exp,
                })
        biz_df = pd.DataFrame(biz_data)

        selected_biz = st.selectbox("事業を選択", list(BIZ_NAMES.values()), index=0, key="hosp_biz_select")
        biz_sel = biz_df[biz_df["事業"] == selected_biz]

        fig_biz = go.Figure()
        fig_biz.add_trace(go.Bar(name="収益", x=biz_sel["年度"], y=biz_sel["収益"], marker_color="#0072B2"))
        fig_biz.add_trace(go.Bar(name="費用", x=biz_sel["年度"], y=biz_sel["費用"], marker_color="#D55E00"))
        fig_biz.update_layout(
            title=f"{selected_biz} - 収益 vs 費用",
            barmode="group",
            yaxis_title="金額（千円）",
        )
        st.plotly_chart(fig_biz, use_container_width=True)

        # 全事業の損益一覧
        st.subheader("全事業 損益一覧")
        pivot = biz_df.pivot_table(index="事業", columns="年度", values="損益", aggfunc="sum")
        pivot = pivot[_fy_labels_list()]

        st.dataframe(pivot.style.format("{:,.0f}").map(
            lambda v: "color: #D55E00" if v < 0 else "color: #0072B2"
        ), use_container_width=True)

        # 事業構成比
        st.subheader("事業別 収益構成比")
        rev_biz = biz_df[["年度", "事業", "収益"]].copy()
        fig_stack = px.bar(
            rev_biz, x="年度", y="収益", color="事業",
            title="事業別 収益構成（積み上げ）",
            labels={"収益": "金額（千円）"},
        )
        fig_stack.update_layout(barmode="stack")
        st.plotly_chart(fig_stack, use_container_width=True)

    # ==============================================================
    # タブ4: 費用構造
    # ==============================================================
    with tab4:
        st.subheader("病院本体 医業費用の内訳")

        cost_items_list = ["給与費", "材料費", "経費", "減価償却費", "資産減耗費", "研究研修費", "医師確保対策費"]
        cost_data = []
        for fy in FY_ORDER:
            for ci in cost_items_list:
                val = items[
                    (items["fiscal_year"] == fy) & (items["section"] == "収益的支出") &
                    (items["kwan_no"] == 1) & (items["kou_no"] == 1) &
                    (items["level"] == "目") & (items["moku_name"] == ci)
                ]["amount"].sum()
                cost_data.append({"年度": _fy_label(fy), "費目": ci, "金額": val})
        cost_df = pd.DataFrame(cost_data)

        fig_cost = px.bar(
            cost_df, x="年度", y="金額", color="費目",
            title="医業費用の内訳推移",
            labels={"金額": "金額（千円）"},
        )
        fig_cost.update_layout(barmode="stack")
        st.plotly_chart(fig_cost, use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l:
            sel_fy_pie = st.selectbox("年度を選択（パイチャート）", _fy_labels_list(), index=4, key="hosp_pie_fy")
        pie_data = cost_df[cost_df["年度"] == sel_fy_pie]
        with col_r:
            fig_pie = px.pie(
                pie_data, names="費目", values="金額",
                title=f"{sel_fy_pie} 医業費用の構成比",
            )
            fig_pie.update_traces(textposition="inside", textinfo="label+percent")
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("主要費目の推移")
        main_costs = cost_df[cost_df["費目"].isin(["給与費", "材料費", "経費", "減価償却費"])]
        fig_line = px.line(
            main_costs, x="年度", y="金額", color="費目",
            markers=True,
            title="主要費目の推移",
            labels={"金額": "金額（千円）"},
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ==============================================================
    # タブ5: 資本的収支
    # ==============================================================
    with tab5:
        st.subheader("資本的収支")

        cap_df = cap_summary.copy()
        cap_df["年度"] = cap_df["fiscal_year"].map(_fy_label)

        fig_cap = go.Figure()
        fig_cap.add_trace(go.Bar(name="資本的収入", x=cap_df["年度"], y=cap_df["total_revenue"], marker_color="#648FFF"))
        fig_cap.add_trace(go.Bar(name="資本的支出", x=cap_df["年度"], y=cap_df["total_expenditure"], marker_color="#FFB000"))
        fig_cap.add_trace(go.Bar(name="不足額", x=cap_df["年度"], y=cap_df["deficit"], marker_color="#D55E00"))
        fig_cap.update_layout(
            title="資本的収入・支出・不足額の推移",
            barmode="group",
            yaxis_title="金額（千円）",
        )
        st.plotly_chart(fig_cap, use_container_width=True)

        st.subheader("資本的収支の内訳")

        cap_detail = []
        for fy in FY_ORDER:
            bond_in = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的収入") &
                (items["level"] == "款") & (items["kwan_name"] == "企業債")
            ]["amount"].sum()
            invest = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的収入") &
                (items["level"] == "款") & (items["kwan_name"] == "出資金")
            ]["amount"].sum()
            construction = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的支出") &
                (items["level"] == "款") & (items["kwan_name"] == "建設改良費")
            ]["amount"].sum()
            bond_repay_val = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的支出") &
                (items["level"] == "款") & (items["kwan_name"] == "企業債償還金")
            ]["amount"].sum()
            building = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的支出") &
                (items["kwan_no"] == 1) & (items["kou_name"] == "建物改修費") & (items["level"] == "項")
            ]["amount"].sum()
            equipment = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的支出") &
                (items["kwan_no"] == 1) & (items["kou_name"] == "固定資産購入費") & (items["level"] == "項")
            ]["amount"].sum()

            cap_detail.append({
                "年度": _fy_label(fy),
                "企業債借入": bond_in,
                "出資金": invest,
                "建設改良費": construction,
                "建物改修費": building,
                "固定資産購入費": equipment,
                "企業債償還金": bond_repay_val,
            })
        cap_det_df = pd.DataFrame(cap_detail)

        col1, col2 = st.columns(2)
        with col1:
            fig_bond = go.Figure()
            fig_bond.add_trace(go.Bar(name="企業債借入", x=cap_det_df["年度"], y=cap_det_df["企業債借入"], marker_color="#0072B2"))
            fig_bond.add_trace(go.Bar(name="企業債償還金", x=cap_det_df["年度"], y=cap_det_df["企業債償還金"], marker_color="#D55E00"))
            fig_bond.update_layout(title="企業債 借入 vs 償還", barmode="group", yaxis_title="金額（千円）")
            st.plotly_chart(fig_bond, use_container_width=True)
        with col2:
            fig_constr = go.Figure()
            fig_constr.add_trace(go.Bar(name="建物改修費", x=cap_det_df["年度"], y=cap_det_df["建物改修費"], marker_color="#785EF0"))
            fig_constr.add_trace(go.Bar(name="固定資産購入費", x=cap_det_df["年度"], y=cap_det_df["固定資産購入費"], marker_color="#FE6100"))
            fig_constr.update_layout(title="建設改良費の内訳", barmode="stack", yaxis_title="金額（千円）")
            st.plotly_chart(fig_constr, use_container_width=True)

        st.dataframe(cap_det_df.set_index("年度").style.format("{:,.0f}"), use_container_width=True)

    # ==============================================================
    # タブ6: 一般会計依存度
    # ==============================================================
    with tab6:
        st.subheader("一般会計依存度の分析")

        dep_data = []
        for _, row in metrics.iterrows():
            fy = row["fiscal_year"]
            subsidy_rev = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") &
                (items["kwan_no"] == 1) & (items["kou_no"] == 2) & (items["moku_no"] == 1) &
                (items["level"] == "目")
            ]["amount"].sum()
            invest_cap = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的収入") &
                (items["level"] == "款") & (items["kwan_name"] == "出資金")
            ]["amount"].sum()
            subsidy_cap = items[
                (items["fiscal_year"] == fy) & (items["section"] == "資本的収入") &
                (items["level"] == "款") & (items["kwan_name"] == "補助金")
            ]["amount"].sum()
            rev_total_val = items[
                (items["fiscal_year"] == fy) & (items["section"] == "収益的収入") & (items["level"] == "款")
            ]["amount"].sum()
            ga_subsidy = row["general_account_subsidy"]
            dep_ratio = ga_subsidy / rev_total_val * 100 if rev_total_val > 0 else 0

            dep_data.append({
                "年度": _fy_label(fy),
                "収益的補助金": subsidy_rev,
                "資本的出資金": invest_cap,
                "資本的補助金": subsidy_cap,
                "一般会計繰出合計": ga_subsidy,
                "繰出依存度(%)": round(dep_ratio, 1),
                "収益的収入合計": rev_total_val,
            })
        dep_df = pd.DataFrame(dep_data)

        fig_dep = go.Figure()
        fig_dep.add_trace(go.Bar(name="収益的補助金", x=dep_df["年度"], y=dep_df["収益的補助金"], marker_color="#648FFF"))
        fig_dep.add_trace(go.Bar(name="資本的出資金", x=dep_df["年度"], y=dep_df["資本的出資金"], marker_color="#0072B2"))
        fig_dep.add_trace(go.Bar(name="資本的補助金", x=dep_df["年度"], y=dep_df["資本的補助金"], marker_color="#FFB000"))
        fig_dep.update_layout(
            title="一般会計からの繰入内訳",
            barmode="stack",
            yaxis_title="金額（千円）",
        )
        st.plotly_chart(fig_dep, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_ratio = px.line(
                dep_df, x="年度", y="繰出依存度(%)",
                markers=True,
                title="一般会計繰出依存度の推移",
            )
            fig_ratio.update_layout(yaxis_title="繰出依存度(%)")
            st.plotly_chart(fig_ratio, use_container_width=True)
        with col2:
            fig_ga = px.bar(
                dep_df, x="年度", y="一般会計繰出合計",
                title="一般会計繰出金の推移",
                labels={"一般会計繰出合計": "金額（千円）"},
            )
            st.plotly_chart(fig_ga, use_container_width=True)

        st.dataframe(
            dep_df[["年度", "収益的補助金", "資本的出資金", "資本的補助金", "一般会計繰出合計", "収益的収入合計", "繰出依存度(%)"]].set_index("年度").style.format({
                "収益的補助金": "{:,.0f}",
                "資本的出資金": "{:,.0f}",
                "資本的補助金": "{:,.0f}",
                "一般会計繰出合計": "{:,.0f}",
                "収益的収入合計": "{:,.0f}",
                "繰出依存度(%)": "{:.1f}",
            }),
            use_container_width=True,
        )
