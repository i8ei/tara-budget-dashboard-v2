#!/usr/bin/env python3
"""太良町 令和8年度 予算ダッシュボード"""
import sqlite3
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budget_r8.db")

# ── ページ設定 ──
st.set_page_config(
    page_title="太良町 予算ダッシュボード",
    page_icon="🏛️",
    layout="wide",
)

# ── カスタムCSS ──
st.markdown("""
<style>
    .block-container { padding-top: 1rem; max-width: 1100px; }
    .hero-number { font-size: 3.2rem; font-weight: 800; color: #1e3a5f; line-height: 1.1; }
    .hero-label { font-size: 1rem; color: #64748b; margin-bottom: 4px; }
    .hero-sub { font-size: 1rem; color: #22c55e; font-weight: 500; }
    .hero-sub.minus { color: #f43f5e; }
    .hero-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px 28px;
        text-align: center;
        margin-bottom: 8px;
    }
    .highlight-box {
        background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
        font-size: 0.95rem;
        line-height: 1.7;
        color: #1e293b;
    }
    .highlight-box strong { color: #1e3a5f; }
    .highlight-box .num { font-weight: 700; color: #2563eb; }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
        margin: 2rem 0 0.5rem 0;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 1rem;
    }

    /* ── スマホ対応 ── */
    @media (max-width: 768px) {
        .block-container { padding-top: 0.5rem; padding-left: 0.5rem; padding-right: 0.5rem; }
        .hero-number { font-size: 2rem; }
        .hero-number span { font-size: 1rem !important; }
        .hero-card { padding: 14px 12px; border-radius: 12px; }
        .hero-label { font-size: 0.85rem; }
        .hero-sub { font-size: 0.85rem; }
        .section-title { font-size: 1rem; margin: 1.2rem 0 0.3rem 0; }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 10px;
            font-size: 0.85rem;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 2px; }
        /* Streamlitのカラムを縦積みに */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 0 0 100% !important;
            min-width: 100% !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def fmt_oku(val, short=False):
    """千円→読みやすい表記に変換。short=Trueはチャートラベル用"""
    oku = val / 100000
    unit_oku = "億" if short else "億円"
    unit_man = "万" if short else "万円"
    if oku >= 1:
        return f"{oku:,.1f}{unit_oku}"
    man = val / 10
    return f"{man:,.0f}{unit_man}"


def fmt_diff(val, short=False):
    """増減額を読みやすく。short=Trueはチャートラベル用（単位省略）"""
    if val == 0:
        return "±0"
    sign = "+" if val > 0 else ""
    oku = abs(val) / 100000
    unit_oku = "億" if short else "億円"
    unit_man = "万" if short else "万円"
    if oku >= 1:
        return f"{sign}{val/100000:,.1f}{unit_oku}"
    man = val / 10
    if abs(man) < 1:
        return "±0"
    return f"{sign}{man:,.0f}{unit_man}"


# ── カラーパレット ──
KUAN_COLORS = [
    "#2563eb",  # 青
    "#f97316",  # オレンジ
    "#22c55e",  # 緑
    "#a855f7",  # 紫
    "#06b6d4",  # シアン
    "#f43f5e",  # ピンク
    "#eab308",  # イエロー
    "#ec4899",  # マゼンタ
    "#14b8a6",  # ティール
    "#6366f1",  # インディゴ
    "#84cc16",  # ライム
    "#f97316",  # オレンジ(2)
    "#8b5cf6",  # バイオレット
    "#94a3b8",  # グレー（その他用）
]

COLOR_INCREASE = "#22c55e"
COLOR_DECREASE = "#f43f5e"

SRC_COLORS = {
    "src_national": "#2563eb",   # 国・県 = 青
    "src_bond": "#f97316",       # 借入 = オレンジ
    "src_other": "#22c55e",      # その他 = 緑
    "src_general": "#94a3b8",    # 一般財源 = グレー
}


# ── 太良町の基本情報 ──
POPULATION = 7_669  # 令和8年1月31日現在


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    summary = pd.read_sql("SELECT * FROM summary", conn)
    revenue = pd.read_sql("SELECT * FROM revenue", conn)
    expenditure = pd.read_sql("SELECT * FROM expenditure", conn)
    conn.close()
    return summary, revenue, expenditure


summary, revenue, expenditure = load_data()

# ── ヘッダー ──
st.markdown("## 太良町 予算ダッシュボード")
st.caption("令和8年度 一般会計")

# ── 歳入/歳出 切替 ──
budget_type = st.radio("", ["歳出", "歳入"], horizontal=True, label_visibility="collapsed")

# ── データ準備 ──
sum_data = summary[summary["type"] == budget_type].copy()
total_current = int(sum_data["amount_current"].sum())
total_previous = int(sum_data["amount_previous"].sum())
diff = total_current - total_previous
diff_pct = diff / total_previous * 100 if total_previous else 0

if budget_type == "歳出":
    detail = expenditure.copy()
else:
    detail = revenue.copy()

# ── ヒーローカード ──
col1, col2 = st.columns([3, 3])

with col1:
    sign_class = "" if diff >= 0 else "minus"
    sign_mark = "+" if diff >= 0 else ""
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-label">予算総額</div>
        <div class="hero-number">{total_current/100000:,.1f}<span style="font-size:1.5rem">億円</span></div>
        <div class="hero-sub {sign_class}">{sign_mark}{diff_pct:.1f}% 前年度比</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    per_capita = total_current * 1000 / POPULATION  # 円
    per_capita_man = per_capita / 10000
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-label">町民1人あたり</div>
        <div class="hero-number" style="font-size:2.6rem">{per_capita_man:,.0f}<span style="font-size:1.3rem">万円</span></div>
        <div class="hero-sub" style="color:#64748b">人口 約{POPULATION:,}人で換算</div>
    </div>
    """, unsafe_allow_html=True)

# ── 注目ポイント ──
if budget_type == "歳出":
    # 歳出の注目データを計算
    top_kuan = sum_data.sort_values("amount_current", ascending=False).iloc[0]
    biggest_diff_row = sum_data.loc[sum_data["diff"].abs().idxmax()]
    bd_val = int(biggest_diff_row["diff"])

    # ふるさと納税関連（総務費の企画財政管理費のsrc_other）
    furusato_revenue = 1_001_000  # 寄附金款の額（千円）
    furusato_pct = furusato_revenue / total_current * 100

    st.markdown(f"""
    <div class="highlight-box">
        <strong>令和8年度 歳出のポイント</strong><br>
        ・最大は<strong>{top_kuan['kuan']}</strong>（{fmt_oku(int(top_kuan['amount_current']))}）。ふるさと納税の返礼品・事務費が大きな割合を占めます<br>
        ・<strong>{biggest_diff_row['kuan']}</strong>が前年から<strong>{fmt_diff(bd_val)}</strong>と最も大きく変動。中学校の学校管理費が約3億円増<br>
        ・町民1人あたり<span class="num">{per_capita_man:,.0f}万円</span>の予算。うち約<span class="num">{int(furusato_pct)}%</span>がふるさと納税由来の財源です
    </div>
    """, unsafe_allow_html=True)
else:
    # 歳入の注目データ
    top_kuan = sum_data.sort_values("amount_current", ascending=False).iloc[0]
    furusato_row = sum_data[sum_data["kuan"] == "寄附金"]
    furusato_amt = int(furusato_row["amount_current"].iloc[0]) if not furusato_row.empty else 0
    furusato_pct = furusato_amt / total_current * 100
    tax_row = sum_data[sum_data["kuan"] == "町税"]
    tax_amt = int(tax_row["amount_current"].iloc[0]) if not tax_row.empty else 0
    tax_per_capita = tax_amt * 1000 / POPULATION / 10000  # 万円

    st.markdown(f"""
    <div class="highlight-box">
        <strong>令和8年度 歳入のポイント</strong><br>
        ・収入の柱は<strong>{top_kuan['kuan']}</strong>（{fmt_oku(int(top_kuan['amount_current']))}）で全体の{int(top_kuan['amount_current'])/total_current*100:.0f}%<br>
        ・<strong>ふるさと納税</strong>（寄附金）は目標額<span class="num">{fmt_oku(furusato_amt)}</span>で歳入の<span class="num">{furusato_pct:.0f}%</span>。太良町の大きな収入源です<br>
        ・町民自身の税負担（町税）は{fmt_oku(tax_amt)}、1人あたり約<span class="num">{tax_per_capita:,.0f}万円</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")

# ── タブ ──
tab1, tab2, tab3 = st.tabs(["全体を見る", "款の中身を見る", "明細を検索する"])

with tab1:
    # ── 款別予算（横棒） ──
    st.markdown('<div class="section-title">款別の予算額</div>', unsafe_allow_html=True)
    chart_data = sum_data.sort_values("amount_current", ascending=False).copy()
    chart_data["label"] = chart_data["amount_current"].apply(lambda x: fmt_oku(x, short=True))

    # 款ごとに色を割り当て
    kuan_order = sum_data.sort_values("amount_current", ascending=False)["kuan"].tolist()
    kuan_color_map = {k: KUAN_COLORS[i % len(KUAN_COLORS)] for i, k in enumerate(kuan_order)}
    chart_data["bar_color"] = chart_data["kuan"].map(kuan_color_map)

    fig_bar = px.bar(
        chart_data, x="amount_current", y="kuan",
        orientation="h",
        color="kuan",
        color_discrete_map=kuan_color_map,
        text="label",
    )
    fig_bar.update_layout(
        height=max(350, len(chart_data) * 36),
        showlegend=False,
        margin=dict(l=0, r=90, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
    )
    fig_bar.update_traces(
        textposition="outside",
        textfont_size=13,
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ── 構成比（ドーナツ） ──
    st.markdown('<div class="section-title">構成比</div>', unsafe_allow_html=True)
    top5 = sum_data.nlargest(5, "amount_current")
    others_total = total_current - int(top5["amount_current"].sum())
    pie_data = pd.concat([
        top5[["kuan", "amount_current"]],
        pd.DataFrame([{"kuan": "その他", "amount_current": others_total}])
    ])
    pie_colors = [kuan_color_map.get(k, "#94a3b8") for k in pie_data["kuan"]]
    fig_pie = px.pie(
        pie_data, values="amount_current", names="kuan",
        color="kuan",
        color_discrete_map={**kuan_color_map, "その他": "#94a3b8"},
        hole=0.5,
    )
    fig_pie.update_layout(
        height=400,
        margin=dict(l=20, r=20, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5, font_size=14),
    )
    fig_pie.update_traces(
        hovertemplate="<b>%{label}</b><br>%{percent}<br>(%{value:,}千円)<extra></extra>",
        textinfo="label+percent",
        textfont_size=13,
    )
    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

    # ── 前年度との比較 ──
    st.markdown('<div class="section-title">前年度との増減</div>', unsafe_allow_html=True)
    comp_data = sum_data.sort_values("diff", ascending=True).copy()
    comp_data["color"] = comp_data["diff"].apply(lambda x: "増加" if x >= 0 else "減少")
    comp_data["label"] = comp_data["diff"].apply(lambda x: fmt_diff(x, short=True))

    fig_comp = px.bar(
        comp_data, x="diff", y="kuan", orientation="h",
        color="color",
        color_discrete_map={"増加": COLOR_INCREASE, "減少": COLOR_DECREASE},
        text="label",
    )
    fig_comp.update_layout(
        height=max(350, len(comp_data) * 36),
        margin=dict(l=0, r=100, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=-0.08, xanchor="center", x=0.5),
    )
    fig_comp.update_traces(
        textposition="outside",
        textfont_size=12,
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    )
    st.plotly_chart(fig_comp, use_container_width=True, config={"displayModeBar": False})

    # ── 歳出の場合は財源内訳 ──
    if budget_type == "歳出":
        st.markdown('<div class="section-title">財源の内訳（どこからお金が来ているか）</div>', unsafe_allow_html=True)
        src_data = sum_data[["kuan", "src_national", "src_bond", "src_other", "src_general"]].copy()
        src_data = src_data.sort_values("src_general", ascending=True)

        fig_src = go.Figure()
        for col, name, color in [
            ("src_national", "国・県からの補助", SRC_COLORS["src_national"]),
            ("src_bond", "借入（地方債）", SRC_COLORS["src_bond"]),
            ("src_other", "その他（寄附金・繰入金等）", SRC_COLORS["src_other"]),
            ("src_general", "町の一般財源", SRC_COLORS["src_general"]),
        ]:
            fig_src.add_trace(go.Bar(
                y=src_data["kuan"], x=src_data[col],
                name=name, orientation="h",
                marker_color=color,
                hovertemplate=f"<b>%{{y}}</b><br>{name}: %{{x:,}}千円<extra></extra>",
            ))
        fig_src.update_layout(
            barmode="stack",
            height=max(350, len(src_data) * 36),
            margin=dict(l=0, r=20, t=10, b=10),
            xaxis=dict(visible=False),
            yaxis=dict(title=""),
            legend=dict(orientation="h", yanchor="bottom", y=-0.12, xanchor="center", x=0.5, font_size=13),
        )
        st.plotly_chart(fig_src, use_container_width=True, config={"displayModeBar": False})

with tab2:
    # ── 款を選んでドリルダウン ──
    selected_kuan = st.selectbox(
        "見たい款を選んでください",
        sum_data.sort_values("kuan_no")["kuan"].tolist(),
    )
    kuan_detail = detail[detail["kuan"] == selected_kuan]

    if not kuan_detail.empty:
        kuan_sum = sum_data[sum_data["kuan"] == selected_kuan].iloc[0]
        kc1, kc2, kc3 = st.columns(3)
        with kc1:
            st.markdown(f"""
            <div class="hero-card">
                <div class="hero-label">本年度</div>
                <div class="hero-number" style="font-size:2rem">{fmt_oku(int(kuan_sum['amount_current']))}</div>
            </div>
            """, unsafe_allow_html=True)
        with kc2:
            st.markdown(f"""
            <div class="hero-card">
                <div class="hero-label">前年度</div>
                <div class="hero-number" style="font-size:2rem; color:#64748b">{fmt_oku(int(kuan_sum['amount_previous']))}</div>
            </div>
            """, unsafe_allow_html=True)
        with kc3:
            d = int(kuan_sum['diff'])
            dc = COLOR_INCREASE if d >= 0 else COLOR_DECREASE
            st.markdown(f"""
            <div class="hero-card">
                <div class="hero-label">増減</div>
                <div class="hero-number" style="font-size:2rem; color:{dc}">{fmt_diff(d)}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")

        # 目別集計
        moku_agg = kuan_detail.groupby(["kou", "moku"]).agg(
            amount_current=("amount_current", "first"),
        ).reset_index().drop_duplicates().sort_values("amount_current", ascending=False)

        st.markdown(f'<div class="section-title">{selected_kuan} の目別内訳</div>', unsafe_allow_html=True)

        show_moku = moku_agg.head(15).copy()
        show_moku = show_moku.sort_values("amount_current", ascending=True)
        show_moku["label"] = show_moku["amount_current"].apply(lambda x: fmt_oku(x, short=True))

        fig_moku = px.bar(
            show_moku, x="amount_current", y="moku", orientation="h",
            color="kou",
            labels={"moku": "", "kou": "項"},
            text="label",
        )
        fig_moku.update_layout(
            height=max(300, len(show_moku) * 38),
            margin=dict(l=0, r=80, t=10, b=10),
            xaxis=dict(visible=False),
            yaxis=dict(title=""),
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, font_size=13),
        )
        fig_moku.update_traces(
            textposition="outside",
            textfont_size=12,
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
        )
        st.plotly_chart(fig_moku, use_container_width=True, config={"displayModeBar": False})

        # 節レベルのテーブル
        st.markdown(f'<div class="section-title">{selected_kuan} の明細</div>', unsafe_allow_html=True)
        cols_show = ["kou", "moku", "setsu", "setsu_amount", "description"]
        if budget_type == "歳出":
            cols_show = ["kou", "moku", "setsu", "setsu_amount", "src_general", "description"]
        rename_map = {
            "kou": "項", "moku": "目", "setsu": "節", "setsu_amount": "金額(千円)",
            "src_general": "一般財源",
            "description": "説明",
        }
        display_df = kuan_detail[cols_show].rename(columns=rename_map)
        st.dataframe(display_df, use_container_width=True, height=500)

with tab3:
    # ── 検索 ──
    search_query = st.text_input("キーワードで検索", "", placeholder="例: 補助金、道路、学校...")

    if search_query:
        # 全カラムを結合した検索用テキストを作成
        search_text = (
            detail["kuan"].fillna("") + " " +
            detail["kou"].fillna("") + " " +
            detail["moku"].fillna("") + " " +
            detail["setsu"].fillna("") + " " +
            detail["description"].fillna("")
        ).str.lower()

        # スペース区切りでAND検索（各キーワードがどこかに含まれればOK）
        keywords = search_query.lower().split()
        mask = pd.Series(True, index=detail.index)
        for kw in keywords:
            mask &= search_text.str.contains(kw, na=False)
        filtered = detail[mask]
        st.markdown(f'**「{search_query}」の検索結果: {len(filtered)}件**')
    else:
        filtered = detail
        st.markdown(f"**全{len(filtered)}件**（キーワードを入力すると絞り込めます）")

    cols_all = ["kuan", "kou", "moku", "setsu", "setsu_amount", "description"]
    rename_all = {
        "kuan": "款", "kou": "項", "moku": "目", "setsu": "節",
        "setsu_amount": "金額(千円)", "description": "説明",
    }
    show_df = filtered[cols_all].rename(columns=rename_all).sort_values("金額(千円)", ascending=False)
    st.dataframe(show_df, use_container_width=True, height=600)

    csv = show_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSV出力", csv, "budget_detail.csv", "text/csv")

# ── フッター ──
st.markdown("---")
st.caption("太良町の予算データを町民の皆さまに分かりやすくお届けするための可視化ツールです。データは公式の予算書に基づいています。")
st.caption("正式なデータは原本（予算書）をご確認ください。 | [令和8年度予算書（町公式）](https://www.town.tara.lg.jp/chosei/_1726/_2042/_7492.html)")
st.caption("© 2026 太良町議会議員 山口一生 | Powered by Streamlit")
