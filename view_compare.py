#!/usr/bin/env python3
"""太良町 予算ダッシュボード — 3年比較ビュー（v3の5タブ）"""
import sqlite3
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st
from plotly.subplots import make_subplots

from common import (
    BASE_DIR, DB_PATHS, YEARS, YEAR_SHORT, YEAR_COLORS,
    KUAN_COLLOQUIAL, NATURE_MAP, SETSU_TO_NATURE, NATURE_COLORS,
    INDEPENDENT_REVENUE, DEPENDENT_REVENUE, KUAN_COLORS,
    COLOR_INCREASE, COLOR_DECREASE,
    safe_pct, fmt_oku, fmt_diff, kuan_with_colloquial, classify_revenue,
    diff_pct_str, diff_color,
)


@st.cache_data
def load_multi_year():
    summaries, revenues, expenditures = [], [], []
    for year_label, db_path in DB_PATHS.items():
        conn = sqlite3.connect(db_path)
        s = pd.read_sql("SELECT * FROM summary", conn)
        r = pd.read_sql("SELECT * FROM revenue", conn)
        e = pd.read_sql("SELECT * FROM expenditure", conn)
        conn.close()
        s["year"] = year_label
        r["year"] = year_label
        e["year"] = year_label
        summaries.append(s); revenues.append(r); expenditures.append(e)
    return pd.concat(summaries), pd.concat(revenues), pd.concat(expenditures)


def render():
    summary_all, revenue_all, expenditure_all = load_multi_year()

    st.markdown("## 太良町 予算ダッシュボード（3年比較）")
    st.caption("令和6年度（2024）・令和7年度（2025）・令和8年度（2026）の一般会計当初予算を横串で比較")

    # ── 年度別総額 ──
    totals = {}
    for y in YEARS:
        s = summary_all[(summary_all["year"] == y) & (summary_all["type"] == "歳出")]
        totals[y] = int(s["amount_current"].sum())

    cols = st.columns(3)
    for i, y in enumerate(YEARS):
        total = totals[y]
        with cols[i]:
            if i == 0:
                sub = ""
            else:
                prev = totals[YEARS[i-1]]
                d = total - prev
                pct = safe_pct(d, prev)
                sign = "+" if d >= 0 else ""
                cls = "plus" if d >= 0 else "minus"
                sub = f'<div class="hero-sub {cls}">前年度比 {sign}{pct:.1f}%（{fmt_diff(d)}）</div>'
            st.markdown(f"""
            <div class="hero-card">
                <div class="hero-label">{y}</div>
                <div class="hero-number">{total/100000:,.1f}<span style="font-size:1rem">億円</span></div>
                {sub}
            </div>
            """, unsafe_allow_html=True)

    # ── タブ ──
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "概況・トレンド", "歳入比較", "歳出比較", "重点変化分析", "予算検索",
    ])

    sum_exp_all = summary_all[summary_all["type"] == "歳出"].copy()
    sum_rev_all = summary_all[summary_all["type"] == "歳入"].copy()

    _r8_exp = sum_exp_all[sum_exp_all["year"] == "R8 (2026)"].sort_values("amount_current", ascending=False)
    kuan_order = _r8_exp["kuan"].tolist()
    kuan_color_map = {k: KUAN_COLORS[i % len(KUAN_COLORS)] for i, k in enumerate(kuan_order)}

    # ═══════════════════════════════════════
    # Tab 1: 概況・3年トレンド
    # ═══════════════════════════════════════
    with tab1:
        pivot_exp = sum_exp_all.pivot_table(
            index=["kuan_no", "kuan"], columns="year", values="amount_current", aggfunc="sum"
        ).reset_index().sort_values("kuan_no")
        for y in YEARS:
            if y not in pivot_exp.columns:
                pivot_exp[y] = 0
        pivot_exp = pivot_exp.fillna(0)
        pivot_exp["R6→R8増減率"] = pivot_exp.apply(
            lambda r: diff_pct_str(r["R8 (2026)"], r["R6 (2024)"]), axis=1)
        pivot_exp["口語"] = pivot_exp["kuan"].map(KUAN_COLLOQUIAL).fillna("")

        st.markdown('<div class="section-title">3年間の主な変化</div>', unsafe_allow_html=True)

        _t_r6 = int(pivot_exp["R6 (2024)"].sum())
        _t_r8 = int(pivot_exp["R8 (2026)"].sum())
        _t_diff = _t_r8 - _t_r6
        _t_pct = safe_pct(_t_diff, _t_r6)

        _pe = pivot_exp.copy()
        _pe["diff"] = _pe["R8 (2026)"] - _pe["R6 (2024)"]
        _pe["diff_pct"] = _pe.apply(
            lambda r: ((r["R8 (2026)"] - r["R6 (2024)"]) / r["R6 (2024)"] * 100) if r["R6 (2024)"] > 0 else 0, axis=1)
        _top_inc = _pe.nlargest(1, "diff").iloc[0]
        _top_dec = _pe.nsmallest(1, "diff").iloc[0]

        _pe["share_r6"] = safe_pct(_pe["R6 (2024)"], _t_r6)
        _pe["share_r8"] = safe_pct(_pe["R8 (2026)"], _t_r8)
        _pe["share_shift"] = _pe["share_r8"] - _pe["share_r6"]
        _top_shift_up = _pe.nlargest(1, "share_shift").iloc[0]
        _top_shift_dn = _pe.nsmallest(1, "share_shift").iloc[0]

        _pe["rank_r6"] = _pe["R6 (2024)"].rank(ascending=False).astype(int)
        _pe["rank_r8"] = _pe["R8 (2026)"].rank(ascending=False).astype(int)
        _pe["rank_change"] = _pe["rank_r6"] - _pe["rank_r8"]
        _rank_up = _pe[_pe["rank_change"] > 0].nlargest(1, "rank_change")

        summary_lines = []
        _sign = "増加" if _t_diff > 0 else "減少"
        summary_lines.append(
            f'予算総額は<span class="num">{fmt_oku(_t_r6)}</span>→<span class="num">{fmt_oku(_t_r8)}</span>へ'
            f'<span class="num">{fmt_diff(_t_diff)}</span>（{_t_pct:+.1f}%）{_sign}。')

        _inc_collq = KUAN_COLLOQUIAL.get(_top_inc["kuan"], "")
        _dec_collq = KUAN_COLLOQUIAL.get(_top_dec["kuan"], "")
        summary_lines.append(
            f'最も増えたのは<b>{_top_inc["kuan"]}</b>（{_inc_collq}）で<span class="num">{fmt_diff(int(_top_inc["diff"]))}</span>（{_top_inc["diff_pct"]:+.1f}%）。'
            f'最も減ったのは<b>{_top_dec["kuan"]}</b>（{_dec_collq}）で<span class="num">{fmt_diff(int(_top_dec["diff"]))}</span>。')
        summary_lines.append(
            f'歳出に占める割合は<b>{_top_shift_up["kuan"]}</b>が{_top_shift_up["share_shift"]:+.1f}pt拡大、'
            f'<b>{_top_shift_dn["kuan"]}</b>が{_top_shift_dn["share_shift"]:+.1f}pt縮小。')
        if not _rank_up.empty:
            _ru = _rank_up.iloc[0]
            summary_lines.append(f'順位では<b>{_ru["kuan"]}</b>が{int(_ru["rank_r6"])}位→{int(_ru["rank_r8"])}位に浮上。')

        st.markdown('<div class="highlight-box">' + "<br>".join(summary_lines) + '</div>', unsafe_allow_html=True)

        # ── ヒートマップ ──
        st.markdown('<div class="section-title">款別歳出の増減ヒートマップ</div>', unsafe_allow_html=True)
        st.caption("色で増減を直感的に把握。赤=増加、青=減少。変化率(%)で着色")

        hm_data = pivot_exp[["kuan", "R6 (2024)", "R7 (2025)", "R8 (2026)"]].copy()
        hm_data["R6→R7 (%)"] = hm_data.apply(lambda r: ((r["R7 (2025)"] - r["R6 (2024)"]) / r["R6 (2024)"] * 100) if r["R6 (2024)"] > 0 else 0, axis=1)
        hm_data["R7→R8 (%)"] = hm_data.apply(lambda r: ((r["R8 (2026)"] - r["R7 (2025)"]) / r["R7 (2025)"] * 100) if r["R7 (2025)"] > 0 else 0, axis=1)
        hm_data["R6→R8 (%)"] = hm_data.apply(lambda r: ((r["R8 (2026)"] - r["R6 (2024)"]) / r["R6 (2024)"] * 100) if r["R6 (2024)"] > 0 else 0, axis=1)
        hm_data = hm_data.sort_values("R8 (2026)", ascending=True)

        hm_labels = [kuan_with_colloquial(k) for k in hm_data["kuan"]]
        hm_z = hm_data[["R6→R7 (%)", "R7→R8 (%)", "R6→R8 (%)"]].values
        hm_text = []
        for _, row in hm_data.iterrows():
            hm_text.append([
                f"{row['R6→R7 (%)']:+.1f}%<br>{fmt_oku(row['R7 (2025)'] - row['R6 (2024)'], short=True)}",
                f"{row['R7→R8 (%)']:+.1f}%<br>{fmt_oku(row['R8 (2026)'] - row['R7 (2025)'], short=True)}",
                f"{row['R6→R8 (%)']:+.1f}%<br>{fmt_oku(row['R8 (2026)'] - row['R6 (2024)'], short=True)}",
            ])

        fig_hm = go.Figure(go.Heatmap(
            z=hm_z, y=hm_labels, x=["R6→R7", "R7→R8", "R6→R8（3年）"],
            text=hm_text, texttemplate="%{text}", textfont=dict(size=11),
            colorscale=[[0, "#2563eb"], [0.5, "#f8fafc"], [1, "#f43f5e"]],
            zmid=0, zmin=-50, zmax=50,
            colorbar=dict(title="増減率(%)", ticksuffix="%"),
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        ))
        fig_hm.update_layout(height=max(400, len(hm_data) * 38), margin=dict(l=0, r=0, t=10, b=10),
                             xaxis=dict(side="top", tickfont=dict(size=13)), yaxis=dict(tickfont=dict(size=12)))
        st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})

        # ── バンプチャート ──
        st.markdown('<div class="section-title">歳出ランキングの変動</div>', unsafe_allow_html=True)
        st.caption("款の予算額順位がR6→R7→R8でどう入れ替わったか。線の交差が順位の逆転")

        bump_kuans = [k for k in pivot_exp["kuan"] if k not in ("予備費", "労働費")]
        bump_data = pivot_exp[pivot_exp["kuan"].isin(bump_kuans)].copy()
        bump_ranks = {}
        for y in YEARS:
            ranked = bump_data[["kuan", y]].sort_values(y, ascending=False).reset_index(drop=True)
            ranked["rank"] = range(1, len(ranked) + 1)
            for _, row in ranked.iterrows():
                bump_ranks.setdefault(row["kuan"], {})[y] = row["rank"]

        fig_bump = go.Figure()
        year_labels_bump = [YEAR_SHORT[y] for y in YEARS]
        bump_colors = {k: KUAN_COLORS[i % len(KUAN_COLORS)] for i, k in enumerate(bump_kuans)}

        for kuan in bump_kuans:
            ranks = [bump_ranks[kuan].get(y, 99) for y in YEARS]
            changed = ranks[0] != ranks[-1]
            width = 4 if changed else 2
            opacity = 1.0 if changed else 0.4
            fig_bump.add_trace(go.Scatter(
                x=year_labels_bump, y=ranks, mode="lines+markers+text", name=kuan,
                line=dict(color=bump_colors[kuan], width=width),
                marker=dict(size=10 if changed else 6, color=bump_colors[kuan]),
                opacity=opacity, text=["", "", f" {kuan}"], textposition="middle right",
                textfont=dict(size=11, color=bump_colors[kuan]),
                hovertemplate="<b>" + kuan + "</b><br>%{x}: %{y}位<extra></extra>", showlegend=False))

        fig_bump.update_layout(height=max(350, len(bump_kuans) * 32), margin=dict(l=10, r=140, t=10, b=10),
                               yaxis=dict(title="順位", autorange="reversed", dtick=1, tickfont=dict(size=11)),
                               xaxis=dict(title="", tickfont=dict(size=15)), plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bump, use_container_width=True, config={"displayModeBar": False})

        # ── 構成比シフト ──
        st.markdown('<div class="section-title">歳出構成比のシフト（R6→R8）</div>', unsafe_allow_html=True)
        st.caption("歳出全体を100%として、各款の割合がどう変わったか。プラス＝拡大、マイナス＝縮小")

        shift_data = pivot_exp[~pivot_exp["kuan"].isin(["予備費", "労働費"])].copy()
        shift_data["R6比率"] = safe_pct(shift_data["R6 (2024)"], _t_r6)
        shift_data["R8比率"] = safe_pct(shift_data["R8 (2026)"], _t_r8)
        shift_data["シフト"] = shift_data["R8比率"] - shift_data["R6比率"]
        shift_data = shift_data.sort_values("シフト")
        shift_data["色"] = shift_data["シフト"].apply(lambda x: "拡大" if x >= 0 else "縮小")
        shift_data["label"] = shift_data["シフト"].apply(lambda x: f"{x:+.1f}pt")
        shift_data["kuan_display"] = shift_data["kuan"].apply(kuan_with_colloquial)

        fig_shift = px.bar(shift_data, x="シフト", y="kuan_display", orientation="h",
                           color="色", text="label", color_discrete_map={"拡大": COLOR_INCREASE, "縮小": COLOR_DECREASE})
        fig_shift.update_layout(height=max(350, len(shift_data) * 32), margin=dict(l=0, r=60, t=10, b=10),
                                xaxis=dict(title="構成比の変化（ポイント）", ticksuffix="pt", zeroline=True, zerolinecolor="#cbd5e1", zerolinewidth=2),
                                yaxis=dict(title="", tickfont=dict(size=11)), showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        fig_shift.update_traces(textposition="outside", textfont_size=11, cliponaxis=False)
        st.plotly_chart(fig_shift, use_container_width=True, config={"displayModeBar": False})

        # ── 款別3年テーブル ──
        st.markdown('<div class="section-title">款別歳出の3年比較</div>', unsafe_allow_html=True)
        st.caption("金額は千円単位。増減率はR6→R8の3年間変化率")

        display_df = pivot_exp[["kuan", "口語", "R6 (2024)", "R7 (2025)", "R8 (2026)", "R6→R8増減率"]].copy()
        display_df.columns = ["款", "内容", "R6 (2024)", "R7 (2025)", "R8 (2026)", "3年増減率"]
        total_row = pd.DataFrame([{
            "款": "合計", "内容": "",
            "R6 (2024)": int(display_df["R6 (2024)"].sum()), "R7 (2025)": int(display_df["R7 (2025)"].sum()),
            "R8 (2026)": int(display_df["R8 (2026)"].sum()),
            "3年増減率": diff_pct_str(int(display_df["R8 (2026)"].sum()), int(display_df["R6 (2024)"].sum())),
        }])
        display_df = pd.concat([display_df, total_row], ignore_index=True)
        for col in ["R6 (2024)", "R7 (2025)", "R8 (2026)"]:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # ── 主要指標の3年推移 ──
        st.markdown('<div class="section-title">主要財政指標の3年推移</div>', unsafe_allow_html=True)

        indicators = []
        for y in YEARS:
            s_rev = sum_rev_all[sum_rev_all["year"] == y].copy()
            s_exp = sum_exp_all[sum_exp_all["year"] == y].copy()
            total_rev = int(s_rev["amount_current"].sum())
            total_exp = int(s_exp["amount_current"].sum())
            s_rev["区分"] = s_rev["kuan"].apply(classify_revenue)
            indep = int(s_rev[s_rev["区分"] == "自主財源"]["amount_current"].sum())
            furusato = int(s_rev[s_rev["kuan"] == "寄附金"]["amount_current"].sum())
            indep_ratio = safe_pct(indep - furusato, total_rev)
            e = expenditure_all[(expenditure_all["year"] == y)].copy()
            e_setsu = e[e["setsu"].notna() & e["setsu_amount"].notna()].copy()
            e_setsu["性質"] = e_setsu["setsu"].map(SETSU_TO_NATURE).fillna("その他")
            n_agg = e_setsu.groupby("性質")["setsu_amount"].sum()
            n_total = n_agg.sum()
            oblig_cats = ["人件費", "扶助費", "公債費"]
            oblig = sum(n_agg.get(c, 0) for c in oblig_cats)
            oblig_ratio = safe_pct(oblig, n_total)
            kouhi = n_agg.get("公債費", 0)
            kouhi_ratio = safe_pct(kouhi, total_exp)
            invest = n_agg.get("投資的経費", 0)
            invest_ratio = safe_pct(invest, n_total)
            indicators.append({
                "年度": YEAR_SHORT[y],
                "自主財源比率\n（ふるさと納税除く）": f"{indep_ratio:.1f}%",
                "義務的経費比率": f"{oblig_ratio:.1f}%",
                "公債費比率": f"{kouhi_ratio:.1f}%",
                "投資的経費比率": f"{invest_ratio:.1f}%",
            })
        st.dataframe(pd.DataFrame(indicators), use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # Tab 2: 歳入比較
    # ═══════════════════════════════════════
    with tab2:
        st.markdown('<div class="section-title">歳入の構成比（3年比較）</div>', unsafe_allow_html=True)
        st.caption("面の膨らみ・縮みで、各財源の割合がどう変化したかがわかります")

        r8_rev = sum_rev_all[sum_rev_all["year"] == "R8 (2026)"].sort_values("amount_current", ascending=False)
        rev_kuan_order = r8_rev["kuan"].tolist()
        major_kuans = r8_rev[r8_rev["amount_current"] >= 50000]["kuan"].tolist()
        rev_comp = sum_rev_all[["kuan", "amount_current", "year"]].copy()
        rev_comp["year_short"] = rev_comp["year"].map(YEAR_SHORT)
        rev_comp["款"] = rev_comp["kuan"].apply(lambda k: k if k in major_kuans else "その他")
        rev_comp_agg = rev_comp.groupby(["year_short", "款"])["amount_current"].sum().reset_index()
        year_totals = rev_comp_agg.groupby("year_short")["amount_current"].sum().to_dict()
        rev_comp_agg["比率"] = rev_comp_agg.apply(lambda r: r["amount_current"] / year_totals[r["year_short"]] * 100, axis=1)

        comp_order = [k for k in rev_kuan_order if k in major_kuans] + ["その他"]
        comp_colors = {k: KUAN_COLORS[i % len(KUAN_COLORS)] for i, k in enumerate(comp_order)}
        comp_colors["その他"] = "#94a3b8"

        fig_comp = go.Figure()
        year_x = ["R6", "R7", "R8"]
        for kuan in reversed(comp_order):
            vals = []
            for ys in year_x:
                row = rev_comp_agg[(rev_comp_agg["year_short"] == ys) & (rev_comp_agg["款"] == kuan)]
                vals.append(float(row["比率"].iloc[0]) if not row.empty else 0)
            fig_comp.add_trace(go.Scatter(
                x=year_x, y=vals, name=kuan, mode="lines", stackgroup="one", groupnorm="percent",
                line=dict(width=0.5, color=comp_colors.get(kuan, "#94a3b8")),
                fillcolor=comp_colors.get(kuan, "#94a3b8"),
                hovertemplate="<b>" + kuan + "</b><br>%{x}: %{y:.1f}%<extra></extra>"))
        fig_comp.update_layout(height=420, margin=dict(l=0, r=0, t=10, b=10),
                               yaxis=dict(title="", ticksuffix="%", range=[0, 100], tickfont=dict(size=11)),
                               xaxis=dict(title="", tickfont=dict(size=16)), legend_title_text="",
                               legend=dict(orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5))
        st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

        src_table = []
        for y in YEARS:
            s = sum_rev_all[sum_rev_all["year"] == y].copy()
            s["区分"] = s["kuan"].apply(classify_revenue)
            indep = int(s[s["区分"] == "自主財源"]["amount_current"].sum())
            dep = int(s[s["区分"] == "依存財源"]["amount_current"].sum())
            total = indep + dep
            src_table.append({"年度": YEAR_SHORT[y], "自主財源": fmt_oku(indep), "依存財源": fmt_oku(dep),
                              "自主比率": f"{safe_pct(indep, total):.1f}%"})
        st.dataframe(pd.DataFrame(src_table), use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">R6→R8 歳入の増減</div>', unsafe_allow_html=True)
        st.caption("3年間で増えた款・減った款を差分だけで表示。バーの長さが変化の大きさ")

        rev_diff = sum_rev_all.pivot_table(index="kuan", columns="year", values="amount_current", aggfunc="sum").reset_index().fillna(0)
        for y in YEARS:
            if y not in rev_diff.columns:
                rev_diff[y] = 0
        rev_diff["diff"] = rev_diff["R8 (2026)"] - rev_diff["R6 (2024)"]
        rev_diff = rev_diff[rev_diff["diff"] != 0].sort_values("diff")
        rev_diff["色"] = rev_diff["diff"].apply(lambda x: "増加" if x > 0 else "減少")
        rev_diff["label"] = rev_diff["diff"].apply(lambda x: fmt_diff(int(x)))

        fig_div = px.bar(rev_diff, x="diff", y="kuan", orientation="h", color="色", text="label",
                         color_discrete_map={"増加": COLOR_INCREASE, "減少": COLOR_DECREASE})
        fig_div.update_layout(height=max(350, len(rev_diff) * 28), margin=dict(l=0, r=70, t=10, b=10),
                              xaxis=dict(visible=False, zeroline=True, zerolinecolor="#cbd5e1", zerolinewidth=2),
                              yaxis=dict(title="", tickfont=dict(size=11)), showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        fig_div.update_traces(textposition="outside", textfont_size=11, cliponaxis=False)
        st.plotly_chart(fig_div, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="section-title">3年間で大きく変わった歳入</div>', unsafe_allow_html=True)
        rev_pivot = sum_rev_all.pivot_table(index=["kuan_no", "kuan"], columns="year", values="amount_current", aggfunc="sum").reset_index().fillna(0)
        for y in YEARS:
            if y not in rev_pivot.columns:
                rev_pivot[y] = 0
        rev_pivot["diff"] = rev_pivot["R8 (2026)"] - rev_pivot["R6 (2024)"]
        rev_pivot["diff_abs"] = rev_pivot["diff"].abs()
        rev_pivot = rev_pivot.sort_values("diff_abs", ascending=False)
        top_changes = rev_pivot.head(7)
        lines = []
        for _, r in top_changes.iterrows():
            d = int(r["diff"])
            if d == 0:
                continue
            arrow = "↑" if d > 0 else "↓"
            color = COLOR_INCREASE if d > 0 else COLOR_DECREASE
            lines.append(f'<b>{r["kuan"]}</b>: <span style="color:{color}">{arrow} {fmt_diff(d)}</span>'
                         f'（{diff_pct_str(r["R8 (2026)"], r["R6 (2024)"])}）')
        if lines:
            st.markdown('<div class="highlight-box">' + "<br>".join(f"・{l}" for l in lines) + '</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">歳入の詳細比較（款を選択）</div>', unsafe_allow_html=True)
        rev_kuans = sorted(sum_rev_all[sum_rev_all["year"] == "R8 (2026)"]["kuan"].unique())
        sel_rev_kuan = st.selectbox("款を選択", rev_kuans, key="rev_kuan_select")
        if sel_rev_kuan:
            rev_detail = revenue_all[revenue_all["kuan"] == sel_rev_kuan].copy()
            rev_moku = rev_detail.groupby(["year", "kuan", "kou", "moku"]).agg(amount=("amount_current", "first")).reset_index()
            rev_moku_pivot = rev_moku.pivot_table(index=["kuan", "kou", "moku"], columns="year", values="amount", aggfunc="sum").reset_index().fillna(0)
            for y in YEARS:
                if y not in rev_moku_pivot.columns:
                    rev_moku_pivot[y] = 0
            rev_moku_pivot["R6→R8"] = rev_moku_pivot.apply(lambda r: diff_pct_str(r["R8 (2026)"], r["R6 (2024)"]), axis=1)
            disp = rev_moku_pivot[["kou", "moku", "R6 (2024)", "R7 (2025)", "R8 (2026)", "R6→R8"]].copy()
            disp.columns = ["項", "目", "R6", "R7", "R8", "増減率"]
            for c in ["R6", "R7", "R8"]:
                disp[c] = disp[c].apply(lambda x: f"{int(x):,}" if x else "0")
            st.dataframe(disp, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # Tab 3: 歳出比較
    # ═══════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-title">款別歳出の3年推移（スモールマルチプル）</div>', unsafe_allow_html=True)
        st.caption("各款の3年間の方向性を個別のミニチャートで一覧。右端の数値はR6→R8の増減率")

        sm_kuans = [k for k in kuan_order if k not in ("予備費", "労働費")]
        n_cols = 3
        n_rows = (len(sm_kuans) + n_cols - 1) // n_cols

        fig_sm = make_subplots(rows=n_rows, cols=n_cols,
                               subplot_titles=[kuan_with_colloquial(k) for k in sm_kuans],
                               vertical_spacing=0.08, horizontal_spacing=0.06)
        year_labels_sm = [YEAR_SHORT[y] for y in YEARS]

        for idx, kuan in enumerate(sm_kuans):
            row = idx // n_cols + 1
            col = idx % n_cols + 1
            vals = []
            for y in YEARS:
                r = sum_exp_all[(sum_exp_all["year"] == y) & (sum_exp_all["kuan"] == kuan)]
                vals.append(int(r["amount_current"].iloc[0]) if not r.empty else 0)
            color = COLOR_INCREASE if vals[-1] >= vals[0] else COLOR_DECREASE
            fig_sm.add_trace(go.Scatter(
                x=year_labels_sm, y=vals, mode="lines+markers+text",
                line=dict(color=color, width=3), marker=dict(size=8, color=color),
                text=[fmt_oku(v, short=True) for v in vals],
                textposition=["bottom center", "top center", "bottom center"],
                textfont=dict(size=10, color=color), showlegend=False,
                hovertemplate=f"<b>{kuan}</b><br>%{{x}}: %{{y:,}}千円<extra></extra>",
            ), row=row, col=col)
            pct = diff_pct_str(vals[-1], vals[0])
            fig_sm.add_annotation(x="R8", y=max(vals), text=f"<b>{pct}</b>", xanchor="left", yanchor="bottom",
                                  showarrow=False, font=dict(size=11, color=color), row=row, col=col)

        fig_sm.update_layout(height=220 * n_rows, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)")
        fig_sm.update_xaxes(tickfont=dict(size=10))
        fig_sm.update_yaxes(visible=False)
        for ann in fig_sm.layout.annotations:
            ann.font = dict(size=12, color="#1e293b")
        st.plotly_chart(fig_sm, use_container_width=True, config={"displayModeBar": False})

        # ── 財源構成の推移 ──
        st.markdown('<div class="section-title">財源構成の推移（歳出）</div>', unsafe_allow_html=True)
        st.caption("歳出を「どこからお金が出ているか」で分解")

        src_labels = {"src_national": "国県支出金", "src_bond": "地方債", "src_other": "その他特定", "src_general": "一般財源"}
        src_colors = {"国県支出金": "#2563eb", "地方債": "#f97316", "その他特定": "#22c55e", "一般財源": "#94a3b8"}

        fsrc_data = []
        for y in YEARS:
            s = sum_exp_all[sum_exp_all["year"] == y]
            for col_name, label in src_labels.items():
                amt = int(s[col_name].fillna(0).sum())
                fsrc_data.append({"年度": YEAR_SHORT[y], "財源": label, "金額": amt})
        fsrc_df = pd.DataFrame(fsrc_data)
        fsrc_total = fsrc_df.groupby("年度")["金額"].sum().to_dict()
        fsrc_df["比率"] = fsrc_df.apply(lambda r: safe_pct(r["金額"], fsrc_total.get(r["年度"], 1)), axis=1)

        fig_fsrc = go.Figure()
        src_order = ["一般財源", "その他特定", "地方債", "国県支出金"]
        for src_name in src_order:
            d = fsrc_df[fsrc_df["財源"] == src_name].sort_values("年度")
            fig_fsrc.add_trace(go.Scatter(
                x=d["年度"], y=d["比率"], mode="lines", name=src_name, stackgroup="one", groupnorm="percent",
                line=dict(width=0.5, color=src_colors.get(src_name, "#94a3b8")),
                fillcolor=src_colors.get(src_name, "#94a3b8"),
                hovertemplate=f"<b>{src_name}</b><br>%{{x}}: %{{y:.1f}}%<extra></extra>"))
        fig_fsrc.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=10),
                               yaxis=dict(title="構成比 (%)", ticksuffix="%", range=[0, 100]),
                               xaxis=dict(title=""), legend_title_text="",
                               legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        st.plotly_chart(fig_fsrc, use_container_width=True, config={"displayModeBar": False})

        # ── 性質別推移 ──
        st.markdown('<div class="section-title">性質別分類の3年推移</div>', unsafe_allow_html=True)
        st.caption("人件費・物件費・公債費など、お金の使い方で分類した推移")

        nature_data = []
        for y in YEARS:
            e = expenditure_all[expenditure_all["year"] == y].copy()
            e_s = e[e["setsu"].notna() & e["setsu_amount"].notna()].copy()
            e_s["性質"] = e_s["setsu"].map(SETSU_TO_NATURE).fillna("その他")
            n_agg = e_s.groupby("性質")["setsu_amount"].sum().reset_index()
            n_agg.columns = ["性質", "金額"]
            n_agg["年度"] = YEAR_SHORT[y]
            nature_data.append(n_agg)
        nature_df = pd.concat(nature_data)
        r8_nature = nature_df[nature_df["年度"] == "R8"].sort_values("金額", ascending=False)
        nature_order = r8_nature["性質"].tolist()

        nature_hm = nature_df.pivot_table(index="性質", columns="年度", values="金額", aggfunc="sum").fillna(0)
        nature_hm = nature_hm.reindex(list(reversed(nature_order)))
        nature_hm_pct = nature_hm.copy()
        if "R6" in nature_hm.columns and "R7" in nature_hm.columns:
            nature_hm_pct["R6→R7"] = nature_hm.apply(lambda r: ((r["R7"] - r["R6"]) / r["R6"] * 100) if r["R6"] > 0 else 0, axis=1)
        if "R7" in nature_hm.columns and "R8" in nature_hm.columns:
            nature_hm_pct["R7→R8"] = nature_hm.apply(lambda r: ((r["R8"] - r["R7"]) / r["R7"] * 100) if r["R7"] > 0 else 0, axis=1)

        hm_nature_z = nature_hm_pct[["R6→R7", "R7→R8"]].values if "R6→R7" in nature_hm_pct.columns else []
        hm_nature_text = []
        for idx_n in nature_hm_pct.index:
            row_t = []
            for pc in ["R6→R7", "R7→R8"]:
                if pc in nature_hm_pct.columns:
                    v = nature_hm_pct.loc[idx_n, pc]
                    row_t.append(f"{v:+.1f}%")
            hm_nature_text.append(row_t)

        if len(hm_nature_z) > 0:
            fig_nature_hm = go.Figure(go.Heatmap(
                z=hm_nature_z, y=list(nature_hm_pct.index), x=["R6→R7", "R7→R8"],
                text=hm_nature_text, texttemplate="%{text}", textfont=dict(size=13),
                colorscale=[[0, "#2563eb"], [0.5, "#f8fafc"], [1, "#f43f5e"]],
                zmid=0, zmin=-30, zmax=30, colorbar=dict(title="増減率(%)", ticksuffix="%")))
            fig_nature_hm.update_layout(height=max(300, len(nature_order) * 38), margin=dict(l=0, r=0, t=10, b=10),
                                        xaxis=dict(side="top", tickfont=dict(size=14)), yaxis=dict(tickfont=dict(size=12)))
            st.plotly_chart(fig_nature_hm, use_container_width=True, config={"displayModeBar": False})

        nature_pivot = nature_df.pivot_table(index="性質", columns="年度", values="金額", aggfunc="sum").reset_index().fillna(0)
        for c in ["R6", "R7", "R8"]:
            if c not in nature_pivot.columns:
                nature_pivot[c] = 0
        nature_pivot["R6→R8"] = nature_pivot.apply(lambda r: diff_pct_str(r["R8"], r["R6"]), axis=1)
        nature_pivot = nature_pivot.sort_values("R8", ascending=False)
        disp_n = nature_pivot.copy()
        for c in ["R6", "R7", "R8"]:
            disp_n[c] = disp_n[c].apply(lambda x: f"{int(x):,}")
        st.dataframe(disp_n, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">歳出の詳細比較（款を選択）</div>', unsafe_allow_html=True)
        exp_kuans = [k for k in kuan_order if k in sum_exp_all["kuan"].unique()]
        sel_exp_kuan = st.selectbox("款を選択", exp_kuans, key="exp_kuan_select")
        if sel_exp_kuan:
            exp_detail = expenditure_all[expenditure_all["kuan"] == sel_exp_kuan].copy()
            exp_moku = exp_detail.groupby(["year", "kuan", "kou", "moku"]).agg(amount=("amount_current", "first")).reset_index()
            exp_moku_pivot = exp_moku.pivot_table(index=["kuan", "kou", "moku"], columns="year", values="amount", aggfunc="sum").reset_index().fillna(0)
            for y in YEARS:
                if y not in exp_moku_pivot.columns:
                    exp_moku_pivot[y] = 0
            exp_moku_pivot["R6→R8"] = exp_moku_pivot.apply(lambda r: diff_pct_str(r["R8 (2026)"], r["R6 (2024)"]), axis=1)
            disp_e = exp_moku_pivot[["kou", "moku", "R6 (2024)", "R7 (2025)", "R8 (2026)", "R6→R8"]].copy()
            disp_e.columns = ["項", "目", "R6", "R7", "R8", "増減率"]
            disp_e = disp_e.sort_values(["項", "目"])
            for c in ["R6", "R7", "R8"]:
                disp_e[c] = disp_e[c].apply(lambda x: f"{int(x):,}" if x else "0")
            st.dataframe(disp_e, use_container_width=True, hide_index=True)

    # ═══════════════════════════════════════
    # Tab 4: 重点変化分析
    # ═══════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-title">予算の規模と変化（バブルチャート）</div>', unsafe_allow_html=True)
        st.caption("横軸＝3年間の増減率、縦軸＝R8の予算規模、円の大きさ＝増減額。右上にあるほど「大きくて伸びている」事業")

        moku_all = expenditure_all.groupby(["year", "kuan", "kou", "moku"]).agg(amount=("amount_current", "first")).reset_index()
        moku_pivot = moku_all.pivot_table(index=["kuan", "kou", "moku"], columns="year", values="amount", aggfunc="sum").reset_index().fillna(0)
        for y in YEARS:
            if y not in moku_pivot.columns:
                moku_pivot[y] = 0
        moku_pivot["diff"] = moku_pivot["R8 (2026)"] - moku_pivot["R6 (2024)"]
        moku_pivot["diff_abs"] = moku_pivot["diff"].abs()

        bubble = moku_pivot[(moku_pivot["R6 (2024)"] > 0) & (moku_pivot["R8 (2026)"] >= 5000)].copy()
        bubble["増減率"] = (bubble["R8 (2026)"] - bubble["R6 (2024)"]) / bubble["R6 (2024)"] * 100
        bubble["R8億"] = bubble["R8 (2026)"] / 100000
        bubble["増減額億"] = bubble["diff_abs"] / 100000
        bubble["size"] = bubble["増減額億"].clip(lower=0.02)
        bubble["色"] = bubble["diff"].apply(lambda x: "増加" if x >= 0 else "減少")

        fig_bubble = px.scatter(bubble, x="増減率", y="R8億", size="size", color="色", hover_name="moku",
                                color_discrete_map={"増加": COLOR_INCREASE, "減少": COLOR_DECREASE}, size_max=50)
        big_items = bubble.nlargest(12, "diff_abs")
        for _, row in big_items.iterrows():
            fig_bubble.add_annotation(x=row["増減率"], y=row["R8億"], text=row["moku"], showarrow=False,
                                      font=dict(size=10, color="#1e293b"), yshift=15)
        fig_bubble.add_vline(x=0, line_dash="dash", line_color="#cbd5e1", line_width=1)
        fig_bubble.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10),
                                 xaxis=dict(title="R6→R8 増減率（%）", ticksuffix="%", zeroline=True),
                                 yaxis=dict(title="R8予算額（億円）", ticksuffix="億"),
                                 showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        fig_bubble.update_traces(marker=dict(opacity=0.7, line=dict(width=1, color="white")),
                                 hovertemplate="<b>%{hovertext}</b><br>増減率: %{x:.1f}%<br>R8予算: %{y:.2f}億円<extra></extra>")
        st.plotly_chart(fig_bubble, use_container_width=True, config={"displayModeBar": False})

        moku_pivot["増減率"] = moku_pivot.apply(lambda r: diff_pct_str(r["R8 (2026)"], r["R6 (2024)"]), axis=1)

        st.markdown('<div class="section-title">3年間で最も増加した目 Top10</div>', unsafe_allow_html=True)
        st.caption("R6→R8で金額が大きく増えた事業分野")
        top_increase = moku_pivot.sort_values("diff", ascending=False).head(10)
        disp_inc = top_increase[["kuan", "kou", "moku", "R6 (2024)", "R7 (2025)", "R8 (2026)", "diff", "増減率"]].copy()
        disp_inc.columns = ["款", "項", "目", "R6", "R7", "R8", "増減額", "増減率"]
        disp_inc["増減額"] = disp_inc["増減額"].apply(lambda x: fmt_diff(int(x)))
        for c in ["R6", "R7", "R8"]:
            disp_inc[c] = disp_inc[c].apply(lambda x: f"{int(x):,}")
        st.dataframe(disp_inc, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">3年間で最も減少した目 Top10</div>', unsafe_allow_html=True)
        top_decrease = moku_pivot.sort_values("diff", ascending=True).head(10)
        disp_dec = top_decrease[["kuan", "kou", "moku", "R6 (2024)", "R7 (2025)", "R8 (2026)", "diff", "増減率"]].copy()
        disp_dec.columns = ["款", "項", "目", "R6", "R7", "R8", "増減額", "増減率"]
        disp_dec["増減額"] = disp_dec["増減額"].apply(lambda x: fmt_diff(int(x)))
        for c in ["R6", "R7", "R8"]:
            disp_dec[c] = disp_dec[c].apply(lambda x: f"{int(x):,}")
        st.dataframe(disp_dec, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-title">新規に登場した目（R6にはなく、R8にある）</div>', unsafe_allow_html=True)
        new_moku = moku_pivot[(moku_pivot["R6 (2024)"] == 0) & (moku_pivot["R8 (2026)"] > 0)]
        if not new_moku.empty:
            new_disp = new_moku[["kuan", "kou", "moku", "R8 (2026)"]].copy()
            new_disp.columns = ["款", "項", "目", "R8金額"]
            new_disp["R8金額"] = new_disp["R8金額"].apply(lambda x: f"{int(x):,}")
            new_disp = new_disp.sort_values("R8金額", ascending=False)
            st.dataframe(new_disp, use_container_width=True, hide_index=True)
        else:
            st.info("該当なし")

        st.markdown('<div class="section-title">消えた目（R6にあり、R8にはない）</div>', unsafe_allow_html=True)
        gone_moku = moku_pivot[(moku_pivot["R6 (2024)"] > 0) & (moku_pivot["R8 (2026)"] == 0)]
        if not gone_moku.empty:
            gone_disp = gone_moku[["kuan", "kou", "moku", "R6 (2024)"]].copy()
            gone_disp.columns = ["款", "項", "目", "R6金額"]
            gone_disp["R6金額"] = gone_disp["R6金額"].apply(lambda x: f"{int(x):,}")
            gone_disp = gone_disp.sort_values("R6金額", ascending=False)
            st.dataframe(gone_disp, use_container_width=True, hide_index=True)
        else:
            st.info("該当なし")

        # ── サンキー図 ──
        st.markdown("---")
        st.markdown('<div class="section-title">お金の流れ（歳入→歳出サンキー図）</div>', unsafe_allow_html=True)
        st.caption("左が収入源、右が使い道。線の太さが金額の大きさ。年度を切り替えて比較できます")

        sankey_year = st.selectbox("年度を選択", YEARS, index=2, key="sankey_year")
        s_rev_y = sum_rev_all[sum_rev_all["year"] == sankey_year].copy()
        s_exp_y = sum_exp_all[sum_exp_all["year"] == sankey_year].copy()

        rev_categories = {
            "町税": ["町税"], "地方交付税": ["地方交付税"], "ふるさと納税": ["寄附金"],
            "国・県支出金": ["国庫支出金", "県支出金"], "町債（借入）": ["町債"],
            "その他歳入": ["地方譲与税", "利子割交付金", "配当割交付金", "株式等譲渡所得割交付金",
                        "法人事業税交付金", "地方消費税交付金", "環境性能割交付金", "地方特例交付金",
                        "交通安全対策特別交付金", "分担金及び負担金", "使用料及び手数料",
                        "財産収入", "繰入金", "繰越金", "諸収入"],
        }
        rev_cat_amounts = {}
        for cat, kuans in rev_categories.items():
            amt = int(s_rev_y[s_rev_y["kuan"].isin(kuans)]["amount_current"].sum())
            if amt > 0:
                rev_cat_amounts[cat] = amt

        exp_kuan_list = s_exp_y.sort_values("amount_current", ascending=False)["kuan"].tolist()
        exp_kuan_major = [k for k in exp_kuan_list if int(s_exp_y[s_exp_y["kuan"] == k]["amount_current"].iloc[0]) >= 50000]
        exp_kuan_minor = [k for k in exp_kuan_list if k not in exp_kuan_major]

        source_nodes = list(rev_cat_amounts.keys())
        middle_nodes = ["一般財源", "特定財源"]
        target_nodes = exp_kuan_major + (["その他歳出"] if exp_kuan_minor else [])
        all_nodes = source_nodes + middle_nodes + target_nodes
        node_idx = {n: i for i, n in enumerate(all_nodes)}

        rev_node_colors = {"町税": "#22c55e", "地方交付税": "#f97316", "ふるさと納税": "#2563eb",
                           "国・県支出金": "#a855f7", "町債（借入）": "#f43f5e", "その他歳入": "#94a3b8"}
        node_colors = []
        for n in all_nodes:
            if n in rev_node_colors:
                node_colors.append(rev_node_colors[n])
            elif n == "一般財源":
                node_colors.append("#94a3b8")
            elif n == "特定財源":
                node_colors.append("#2563eb")
            elif n in kuan_color_map:
                node_colors.append(kuan_color_map[n])
            else:
                node_colors.append("#94a3b8")

        link_source, link_target, link_value, link_color = [], [], [], []
        total_src_general = int(s_exp_y["src_general"].fillna(0).sum())
        total_src_specific = int(s_exp_y["src_national"].fillna(0).sum()) + int(s_exp_y["src_bond"].fillna(0).sum()) + int(s_exp_y["src_other"].fillna(0).sum())

        fixed_general = {"町税", "地方交付税"}
        fixed_specific = {"国・県支出金", "町債（借入）", "ふるさと納税"}
        fixed_specific_total = sum(v for k, v in rev_cat_amounts.items() if k in fixed_specific)
        other_total = rev_cat_amounts.get("その他歳入", 0)
        other_to_specific = max(0, total_src_specific - fixed_specific_total)
        other_to_general = max(0, other_total - other_to_specific)

        for cat, amt in rev_cat_amounts.items():
            if cat in fixed_general:
                link_source.append(node_idx[cat]); link_target.append(node_idx["一般財源"])
                link_value.append(amt); link_color.append("rgba(148, 163, 184, 0.3)")
            elif cat in fixed_specific:
                link_source.append(node_idx[cat]); link_target.append(node_idx["特定財源"])
                link_value.append(amt); link_color.append("rgba(37, 99, 235, 0.2)")
            elif cat == "その他歳入":
                if other_to_general > 0:
                    link_source.append(node_idx[cat]); link_target.append(node_idx["一般財源"])
                    link_value.append(other_to_general); link_color.append("rgba(148, 163, 184, 0.3)")
                if other_to_specific > 0:
                    link_source.append(node_idx[cat]); link_target.append(node_idx["特定財源"])
                    link_value.append(other_to_specific); link_color.append("rgba(37, 99, 235, 0.2)")

        exp_src = s_exp_y[["kuan", "src_national", "src_bond", "src_other", "src_general"]].copy()
        for _, row in exp_src.iterrows():
            kuan = row["kuan"]
            target = kuan if kuan in exp_kuan_major else "その他歳出"
            if target not in node_idx:
                continue
            gen_val = int(row["src_general"]) if pd.notna(row["src_general"]) else 0
            if gen_val > 0:
                link_source.append(node_idx["一般財源"]); link_target.append(node_idx[target])
                link_value.append(gen_val); link_color.append("rgba(148, 163, 184, 0.25)")
            spec_val = sum(int(row[c]) if pd.notna(row[c]) else 0 for c in ["src_national", "src_bond", "src_other"])
            if spec_val > 0:
                link_source.append(node_idx["特定財源"]); link_target.append(node_idx[target])
                link_value.append(spec_val); link_color.append("rgba(37, 99, 235, 0.15)")

        fig_sankey = go.Figure(go.Sankey(
            arrangement="snap", textfont=dict(size=15, color="#1e293b", family="sans-serif"),
            node=dict(pad=25, thickness=24, line=dict(color="white", width=2),
                      label=all_nodes, color=node_colors,
                      hovertemplate="%{label}<br>%{value:,}千円<extra></extra>"),
            link=dict(source=link_source, target=link_target, value=link_value, color=link_color,
                      hovertemplate="%{source.label} → %{target.label}<br>%{value:,}千円<extra></extra>")))
        fig_sankey.update_layout(height=500, margin=dict(l=10, r=10, t=30, b=10),
                                 font=dict(size=15, color="#1e293b", family="sans-serif"))
        st.plotly_chart(fig_sankey, use_container_width=True, config={"displayModeBar": False})

        _total_rev_y = int(s_rev_y["amount_current"].sum())
        _total_exp_y = int(s_exp_y["amount_current"].sum())
        st.caption(f"{YEAR_SHORT[sankey_year]} 歳入合計: {fmt_oku(_total_rev_y)} / 歳出合計: {fmt_oku(_total_exp_y)}")

    # ═══════════════════════════════════════
    # Tab 5: 予算検索
    # ═══════════════════════════════════════
    with tab5:
        st.markdown('<div class="section-title">予算検索（3年横断）</div>', unsafe_allow_html=True)
        st.caption("キーワードで歳出予算を検索。全年度の結果を比較できます")

        search_query = st.text_input("キーワード（例: 学校、道路、子育て）", key="compare_search_query")
        search_mode = st.radio("検索対象", ["歳出", "歳入"], horizontal=True, key="compare_search_mode")

        if search_query:
            target_df = expenditure_all if search_mode == "歳出" else revenue_all
            mask = pd.Series(False, index=target_df.index)
            for col_name in ["kuan", "kou", "moku", "setsu", "description"]:
                if col_name in target_df.columns:
                    mask = mask | target_df[col_name].astype(str).str.contains(search_query, case=False, na=False)
            results = target_df[mask].copy()

            if results.empty:
                st.warning("該当する項目が見つかりませんでした")
            else:
                st.success(f"{len(results)}件ヒット")
                for y in YEARS:
                    r = results[results["year"] == y]
                    if r.empty:
                        continue
                    st.markdown(f"**{y}**（{len(r)}件）")
                    disp_cols = ["kuan", "kou", "moku", "setsu", "setsu_amount", "description"]
                    disp_names = ["款", "項", "目", "節", "金額", "説明"]
                    available_cols = [c for c in disp_cols if c in r.columns]
                    r_disp = r[available_cols].copy()
                    col_rename = dict(zip(disp_cols, disp_names))
                    r_disp = r_disp.rename(columns={c: col_rename.get(c, c) for c in available_cols})
                    if "金額" in r_disp.columns:
                        r_disp["金額"] = r_disp["金額"].apply(lambda x: f"{int(x):,}" if pd.notna(x) and x != "" else "")
                    st.dataframe(r_disp, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown('<div class="section-title">歳出ドリルダウン</div>', unsafe_allow_html=True)

        drill_mode = st.radio("表示モード", ["全年度比較", "年度別"], horizontal=True, key="drill_mode")
        dd_kuans = sorted(expenditure_all["kuan"].unique())
        dd_kuan = st.selectbox("款", dd_kuans, key="dd_kuan")

        if dd_kuan:
            dd_data = expenditure_all[expenditure_all["kuan"] == dd_kuan].copy()
            dd_kous = sorted(dd_data["kou"].dropna().unique())
            dd_kou = st.selectbox("項（任意）", ["すべて"] + list(dd_kous), key="dd_kou")
            if dd_kou != "すべて":
                dd_data = dd_data[dd_data["kou"] == dd_kou]

            if drill_mode == "全年度比較":
                dd_moku = dd_data.groupby(["year", "kou", "moku"]).agg(amount=("amount_current", "first")).reset_index()
                dd_pivot = dd_moku.pivot_table(index=["kou", "moku"], columns="year", values="amount", aggfunc="sum").reset_index().fillna(0)
                for y in YEARS:
                    if y not in dd_pivot.columns:
                        dd_pivot[y] = 0
                dd_pivot["R6→R8"] = dd_pivot.apply(lambda r: diff_pct_str(r["R8 (2026)"], r["R6 (2024)"]), axis=1)

                def make_sparkline_svg(r6, r7, r8):
                    vals = [r6, r7, r8]
                    max_v = max(vals) if max(vals) > 0 else 1
                    w, h = 80, 24
                    pts = []
                    for i, v in enumerate(vals):
                        x = i * (w / 2)
                        y_pos = h - (v / max_v * (h - 4)) - 2
                        pts.append(f"{x},{y_pos}")
                    color = COLOR_INCREASE if r8 >= r6 else COLOR_DECREASE
                    svg = f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
                    svg += f'<polyline points="{" ".join(pts)}" fill="none" stroke="{color}" stroke-width="2"/>'
                    for pt in pts:
                        svg += f'<circle cx="{pt.split(",")[0]}" cy="{pt.split(",")[1]}" r="3" fill="{color}"/>'
                    svg += '</svg>'
                    return svg

                disp_dd = dd_pivot[["kou", "moku", "R6 (2024)", "R7 (2025)", "R8 (2026)", "R6→R8"]].copy()
                disp_dd.columns = ["項", "目", "R6", "R7", "R8", "増減率"]
                for c in ["R6", "R7", "R8"]:
                    disp_dd[c] = disp_dd[c].apply(lambda x: f"{int(x):,}" if x else "0")
                st.dataframe(disp_dd, use_container_width=True, hide_index=True)

                if len(dd_pivot) <= 30:
                    spark_html = '<div style="margin-top:8px">'
                    for _, row in dd_pivot.iterrows():
                        svg = make_sparkline_svg(row["R6 (2024)"], row["R7 (2025)"], row["R8 (2026)"])
                        pct = diff_pct_str(row["R8 (2026)"], row["R6 (2024)"])
                        color = COLOR_INCREASE if row["R8 (2026)"] >= row["R6 (2024)"] else COLOR_DECREASE
                        spark_html += (
                            f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0;font-size:0.85rem">'
                            f'{svg} <span style="min-width:120px">{row["moku"]}</span>'
                            f' <span style="color:{color};font-weight:600">{pct}</span>'
                            f' <span style="color:#94a3b8">{fmt_oku(row["R6 (2024)"], short=True)}→{fmt_oku(row["R8 (2026)"], short=True)}</span></div>')
                    spark_html += '</div>'
                    st.markdown(spark_html, unsafe_allow_html=True)
            else:
                dd_year = st.selectbox("年度", YEARS, index=2, key="dd_year")
                dd_yr_data = dd_data[dd_data["year"] == dd_year]
                if dd_yr_data.empty:
                    st.info("この年度にはデータがありません")
                else:
                    cols_show = ["kou", "moku", "setsu", "setsu_amount", "description"]
                    available = [c for c in cols_show if c in dd_yr_data.columns]
                    disp_yr = dd_yr_data[available].copy()
                    disp_yr = disp_yr.rename(columns={"kou": "項", "moku": "目", "setsu": "節", "setsu_amount": "金額", "description": "説明"})
                    if "金額" in disp_yr.columns:
                        disp_yr["金額"] = disp_yr["金額"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "")
                    st.dataframe(disp_yr, use_container_width=True, hide_index=True)
