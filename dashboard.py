#!/usr/bin/env python3
"""太良町 令和8年度 予算ダッシュボード v2"""
import sqlite3
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budget_r8.db")

# ── ページ設定 ──
st.set_page_config(
    page_title="太良町 予算ダッシュボード v2",
    page_icon="🏛️",
    layout="wide",
)

# ── 口語化マッピング ──
KUAN_COLLOQUIAL = {
    "議会費": "議会の運営",
    "総務費": "役場の運営・ふるさと納税",
    "民生費": "福祉・医療・子育て",
    "衛生費": "健康・ごみ処理",
    "労働費": "労働対策",
    "農林水産業費": "農業・林業・漁業の振興",
    "商工費": "商工業・観光の振興",
    "土木費": "道路・住宅の整備",
    "消防費": "消防・防災",
    "教育費": "学校・文化・スポーツ",
    "災害復旧費": "災害からの復旧",
    "公債費": "借金の返済",
    "諸支出金": "その他の支出",
    "予備費": "緊急時の備え",
}

# ── 性質別マッピング（節名→カテゴリ） ──
NATURE_MAP = {
    "人件費": ["報酬", "給料", "職員手当等", "共済費"],
    "扶助費": ["扶助費"],
    "公債費": ["償還金利子及び割引料"],
    "物件費": ["需用費", "役務費", "委託料", "使用料及び賃借料"],
    "補助費等": ["負担金補助及び交付金", "報償費"],
    "投資的経費": ["工事請負費", "公有財産購入費", "備品購入費", "原材料費"],
    "積立金・貸付金": ["積立金", "貸付金"],
    "繰出金": ["繰出金"],
    "その他": ["旅費", "補償補填及び賠償金", "公課費", "交際費", "予備費"],
}

# 逆引き辞書
SETSU_TO_NATURE = {}
for cat, setsu_list in NATURE_MAP.items():
    for s in setsu_list:
        SETSU_TO_NATURE[s] = cat

# 性質別カラー
NATURE_COLORS = {
    "人件費": "#2563eb",
    "扶助費": "#f97316",
    "公債費": "#f43f5e",
    "物件費": "#22c55e",
    "補助費等": "#a855f7",
    "投資的経費": "#06b6d4",
    "積立金・貸付金": "#eab308",
    "繰出金": "#ec4899",
    "その他": "#94a3b8",
}

# ── 自主財源 vs 依存財源マッピング ──
INDEPENDENT_REVENUE = [
    "町税", "使用料及び手数料", "財産収入", "寄附金",
    "繰入金", "繰越金", "諸収入", "分担金及び負担金",
]
DEPENDENT_REVENUE = [
    "地方交付税", "国庫支出金", "県支出金", "地方譲与税",
    "利子割交付金", "配当割交付金", "株式等譲渡所得割交付金",
    "法人事業税交付金", "地方消費税交付金", "環境性能割交付金",
    "地方特例交付金", "交通安全対策特別交付金", "町債",
]

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
        border-radius: 12px;
        padding: 24px 28px;
        text-align: center;
        margin-bottom: 8px;
    }
    .indicator-card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: center;
        margin-bottom: 8px;
    }
    .indicator-value { font-size: 2rem; font-weight: 800; color: #1e3a5f; line-height: 1.2; }
    .indicator-label { font-size: 0.85rem; color: #64748b; margin-bottom: 4px; }
    .indicator-sub { font-size: 0.8rem; color: #94a3b8; }
    .highlight-box {
        background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%);
        border-left: 4px solid #2563eb;
        border-radius: 12px;
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

    /* ── チェックリスト ── */
    .check-box {
        background: #fffbeb;
        border: 1px solid #fbbf24;
        border-radius: 12px;
        padding: 20px 24px;
        margin: 16px 0;
    }
    .check-box-title {
        font-size: 1rem;
        font-weight: 700;
        color: #92400e;
        margin-bottom: 12px;
    }
    .check-item {
        font-size: 0.92rem;
        line-height: 1.8;
        color: #1e293b;
        padding: 2px 0;
    }
    .check-item .tag {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 1px 8px;
        border-radius: 4px;
        margin-right: 6px;
        vertical-align: middle;
    }
    .tag-change { background: #fef3c7; color: #92400e; }
    .tag-source { background: #dbeafe; color: #1e40af; }
    .tag-detail { background: #f0fdf4; color: #166534; }


    /* ── インジケーター色バリエーション ── */
    .indicator-value.clr-green { color: #22c55e; }
    .indicator-value.clr-red { color: #f43f5e; }
    .indicator-value.clr-blue { color: #2563eb; }
    .indicator-value.clr-orange { color: #f97316; }
    .indicator-value.clr-cyan { color: #06b6d4; }
    .indicator-value.clr-pink { color: #ec4899; }
    .indicator-value.clr-muted { color: #94a3b8; }

    /* ── サブセクションタイトル ── */
    .section-subtitle {
        font-size: 1rem;
        font-weight: 600;
        color: #475569;
        margin: 1rem 0 0.3rem 0;
    }

    /* ── highlight-box カラーバリアント ── */
    .highlight-box.hl-blue { border-left-color: #3b82f6; }
    .highlight-box.hl-green { border-left-color: #10b981; }

    /* ── スマホ対応 ── */
    @media (max-width: 768px) {
        .block-container { padding-top: 0.5rem; padding-left: 0.5rem; padding-right: 0.5rem; }
        .hero-number { font-size: 2rem; }
        .hero-number span { font-size: 1rem !important; }
        .hero-card { padding: 14px 12px; border-radius: 12px; }
        .indicator-card { padding: 10px 8px; }
        .indicator-value { font-size: 1.5rem; }
        .hero-label { font-size: 0.85rem; }
        .hero-sub { font-size: 0.85rem; }
        .section-title { font-size: 1rem; margin: 1.2rem 0 0.3rem 0; }
        .stTabs [data-baseweb="tab"] {
            padding: 8px 10px;
            font-size: 0.85rem;
        }
        .stTabs [data-baseweb="tab-list"] { gap: 2px; }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important;
            flex: 0 0 100% !important;
            min-width: 100% !important;
        }
        [data-testid="stDataFrame"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
    }

    /* ── スマホ（狭幅）対応 ── */
    @media (max-width: 480px) {
        .hero-number { font-size: 1.6rem; }
        .hero-number span { font-size: 0.8rem !important; }
        .indicator-value { font-size: 1.2rem; }
        .indicator-label { font-size: 0.75rem; }
        .indicator-sub { font-size: 0.7rem; }
        .hero-card { padding: 10px 8px; }
        .indicator-card { padding: 8px 6px; }
        .section-title { font-size: 0.9rem; }
        .section-subtitle { font-size: 0.85rem; }
        .highlight-box { padding: 12px 14px; font-size: 0.85rem; }
        .check-box { padding: 14px 16px; }
        .stTabs [data-baseweb="tab"] {
            padding: 6px 8px;
            font-size: 0.78rem;
        }
    }

    /* ── 用語ツールチップ ── */
    .term-tip { border-bottom: 1px dotted #64748b; cursor: help; position: relative; }
    .term-tip::after {
        content: attr(data-tip);
        position: absolute; bottom: 125%; left: 50%; transform: translateX(-50%);
        background: #1e293b; color: #fff; padding: 6px 12px; border-radius: 6px;
        font-size: 0.8rem; white-space: normal; max-width: 260px;
        opacity: 0; pointer-events: none; transition: opacity 0.2s; z-index: 1000;
    }
    .term-tip:hover::after, .term-tip:active::after { opacity: 1; }
</style>
""", unsafe_allow_html=True)


GLOSSARY = {
    "義務的経費": "法律や契約で支払いが決まっている経費（人件費＋扶助費＋公債費）",
    "扶助費": "生活保護・児童手当・医療費助成など福祉の給付金",
    "性質別": "お金の「使い方」で分けた分類（人件費・工事費など）",
    "自主財源": "町税やふるさと納税など、町が自ら集めるお金",
    "依存財源": "国や県からもらうお金（交付税・補助金・地方債など）",
    "地方交付税": "国が財政力の弱い自治体に配るお金。国からの仕送り",
    "一般財源充当率": "その事業に町の自由に使えるお金をどれだけ充てているかの割合",
    "繰出金": "一般会計から病院や水道など特別会計に回すお金",
    "公債費": "過去に借りたお金の返済。いわば借金の返済",
    "款": "予算の一番大きな分類（例：民生費＝福祉・医療）",
    "項": "款の中の分類（例：民生費→社会福祉費）",
    "目": "項の中のさらに細かい分類",
    "節": "具体的な支出の種類（例：委託料、工事費）",
    "特別会計": "水道・病院・介護保険など特定事業を分けて管理する会計",
    "町債": "町が国の制度に基づいて借りるお金。返済は将来の予算から",
}

def tip(term):
    desc = GLOSSARY.get(term, "")
    return f'<span class="term-tip" data-tip="{desc}">{term}</span>' if desc else term


def safe_pct(part, total):
    """ゼロ除算を防ぐパーセント計算"""
    return part / total * 100 if total else 0.0

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


def kuan_with_colloquial(kuan_name):
    """款名に口語ツールチップ付きで返す"""
    colloquial = KUAN_COLLOQUIAL.get(kuan_name)
    if colloquial:
        return f"{kuan_name}（{colloquial}）"
    return kuan_name


# ── カラーパレット ──
KUAN_COLORS = [
    "#2563eb", "#f97316", "#22c55e", "#a855f7", "#06b6d4",
    "#f43f5e", "#eab308", "#ec4899", "#14b8a6", "#6366f1",
    "#84cc16", "#d97706", "#8b5cf6", "#94a3b8",
]

COLOR_INCREASE = "#22c55e"
COLOR_DECREASE = "#f43f5e"

SRC_COLORS = {
    "src_national": "#2563eb",
    "src_bond": "#f97316",
    "src_other": "#22c55e",
    "src_general": "#94a3b8",
}

# ── 太良町の基本情報（年度更新時はここだけ変更） ──
POPULATION = 7_669
FURUSATO_COST_ITEMS = {
    "返礼品（謝礼）": 300_000,
    "インターネット広告": 112_802,
    "事業支援業務委託": 44_550,
    "ワンストップ特例受付": 8_069,
    "広告謝礼": 500,
}
FURUSATO_FUND_SIM = 1_000_000  # 基金積立額（千円）


@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    summary = pd.read_sql("SELECT * FROM summary", conn)
    expenditure = pd.read_sql("SELECT * FROM expenditure", conn)
    major_projects = pd.read_sql("SELECT * FROM major_projects", conn)
    special_accounts = pd.read_sql("SELECT * FROM special_account_summary", conn)
    conn.close()
    return summary, expenditure, major_projects, special_accounts


summary, expenditure, major_projects, special_accounts = load_data()

# ── ヘッダー ──
st.markdown("## 太良町 令和８年度予算ダッシュボード")
budget_type = "歳出"

# ── データ準備 ──
sum_data = summary[summary["type"] == budget_type].copy()
total_current = int(sum_data["amount_current"].sum())
total_previous = int(sum_data["amount_previous"].sum())
diff = total_current - total_previous
diff_pct = diff / total_previous * 100 if total_previous else 0

sum_exp = summary[summary["type"] == "歳出"].copy()
sum_rev = summary[summary["type"] == "歳入"].copy()
total_exp = int(sum_exp["amount_current"].sum())
total_rev = int(sum_rev["amount_current"].sum())
per_capita = total_current * 1000 / POPULATION
per_capita_man = per_capita / 10000

# ふるさと納税収入（DBから取得、全タブ共通）
_furusato_row = sum_rev[sum_rev["kuan"] == "寄附金"]
FURUSATO_REVENUE = int(_furusato_row["amount_current"].iloc[0]) if not _furusato_row.empty else 0

# ── 自主財源比率（全タブ共通） ──
def classify_revenue(kuan_name):
    if kuan_name in INDEPENDENT_REVENUE:
        return "自主財源"
    elif kuan_name in DEPENDENT_REVENUE:
        return "依存財源"
    return "その他"

rev_summary = summary[summary["type"] == "歳入"].copy()
rev_summary["財源区分"] = rev_summary["kuan"].apply(classify_revenue)

indep_total = int(rev_summary[rev_summary["財源区分"] == "自主財源"]["amount_current"].sum())
dep_total = int(rev_summary[rev_summary["財源区分"] == "依存財源"]["amount_current"].sum())
indep_ratio = safe_pct(indep_total, total_rev)

furusato_amt = int(rev_summary[rev_summary["kuan"] == "寄附金"]["amount_current"].iloc[0]) if not rev_summary[rev_summary["kuan"] == "寄附金"].empty else 0
indep_adjusted = indep_total - furusato_amt
indep_adjusted_ratio = safe_pct(indep_adjusted, total_rev)

detail = expenditure.copy()

# ── 性質別集計（全タブ共通データ） ──
exp_setsu = expenditure[expenditure["setsu"].notna() & (expenditure["setsu_amount"].notna())].copy()
exp_setsu["性質"] = exp_setsu["setsu"].map(SETSU_TO_NATURE).fillna("その他")

nature_agg = exp_setsu.groupby("性質")["setsu_amount"].sum().reset_index()
nature_agg.columns = ["性質", "金額"]
nature_total = int(nature_agg["金額"].sum())
nature_agg = nature_agg.sort_values("金額", ascending=False)

obligatory_cats = ["人件費", "扶助費", "公債費"]
obligatory_total = int(nature_agg[nature_agg["性質"].isin(obligatory_cats)]["金額"].sum())
obligatory_ratio = safe_pct(obligatory_total, nature_total)

investment_total = int(nature_agg[nature_agg["性質"] == "投資的経費"]["金額"].sum())
investment_ratio = safe_pct(investment_total, nature_total)

# 公債費比率（歳出総額ベース）
kouhi_total = int(nature_agg[nature_agg["性質"] == "公債費"]["金額"].sum())
kouhi_ratio = safe_pct(kouhi_total, total_exp)



# ── 指標バー ──
sign_class = "" if diff >= 0 else "minus"
sign_mark = "+" if diff >= 0 else ""
hc1, hc2, hc3 = st.columns(3)
with hc1:
    st.markdown(f"""
    <div class="indicator-card">
        <div class="indicator-label">歳出総額（令和8年度）</div>
        <div class="indicator-value">{total_current/100000:,.1f}<span style="font-size:1rem">億円</span></div>
        <div class="indicator-sub">人口 {POPULATION:,}人</div>
    </div>
    """, unsafe_allow_html=True)
with hc2:
    st.markdown(f"""
    <div class="indicator-card">
        <div class="indicator-label">前年度比</div>
        <div class="indicator-value {sign_class}" style="color:{'#22c55e' if diff >= 0 else '#f43f5e'}">{sign_mark}{diff_pct:.1f}<span style="font-size:1rem">%</span></div>
        <div class="indicator-sub">{fmt_diff(diff)}</div>
    </div>
    """, unsafe_allow_html=True)
with hc3:
    st.markdown(f"""
    <div class="indicator-card">
        <div class="indicator-label">町民1人あたり</div>
        <div class="indicator-value">{per_capita_man:,.0f}<span style="font-size:1rem">万円</span></div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# ── タブ ──
# ═══════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "まとめ", "お金の出入り", "もっと詳しく", "主要な事業",
    "ふるさと納税", "水道・病院など", "予算を調べる",
])

# ── 款の色マップ（全タブ共通） ──
kuan_order = sum_data.sort_values("amount_current", ascending=False)["kuan"].tolist()
kuan_color_map = {k: KUAN_COLORS[i % len(KUAN_COLORS)] for i, k in enumerate(kuan_order)}

# ═══════════════════════════════════════════════════════════
# タブ1: 概況（v1ベース + 口語化ツールチップ）
# ═══════════════════════════════════════════════════════════
with tab1:
    # ── 財政ヘルスメーター ──
    st.markdown('<div class="section-title">財政の健全度チェック</div>', unsafe_allow_html=True)
    _oblig_meaning = f"予算の約{obligatory_ratio:.0f}%は人件費・福祉・借金返済で固定されています"
    _dep_ratio = 100 - indep_adjusted_ratio
    _indep_meaning = f"町税等で{indep_adjusted_ratio:.0f}%を賄い、{_dep_ratio:.0f}%は国・県からの交付金等です"
    _kouhi_oku = fmt_oku(kouhi_total)
    _kouhi_meaning = f"予算のうち{_kouhi_oku}が過去の借入の返済に充てられています"

    hm1, hm2, hm3 = st.columns(3)
    with hm1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">{tip("義務的経費")}比率</div>
            <div class="indicator-value">{obligatory_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">→ {_oblig_meaning}</div>
        </div>
        """, unsafe_allow_html=True)
    with hm2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">{tip("自主財源")}比率（ふるさと納税除く）</div>
            <div class="indicator-value">{indep_adjusted_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">→ {_indep_meaning}</div>
        </div>
        """, unsafe_allow_html=True)
    with hm3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">{tip("公債費")}比率</div>
            <div class="indicator-value">{kouhi_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">→ {_kouhi_meaning}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 町民1人あたり内訳 ──
    st.markdown('<div class="section-title">町民1人あたりの予算 ── あなたの暮らしに使われるお金</div>', unsafe_allow_html=True)
    _pc_data = sum_data[["kuan", "amount_current"]].copy()
    _pc_data["per_capita"] = _pc_data["amount_current"] * 1000 / POPULATION
    _pc_data = _pc_data.sort_values("amount_current", ascending=False)
    _pc_top5 = _pc_data.head(5)
    _pc_lines = []
    for _, r in _pc_top5.iterrows():
        colloquial = KUAN_COLLOQUIAL.get(r["kuan"], r["kuan"])
        _pc_lines.append(f'<b>{r["kuan"]}</b>（{colloquial}）… <span class="num">{r["per_capita"]/10000:.1f}万円</span>')
    st.markdown(
        '<div class="highlight-box">' + "<br>".join(
            [f"・{line}" for line in _pc_lines]
        ) + '</div>',
        unsafe_allow_html=True,
    )

    # 横積み上げバー（1人あたり）
    _pc_bar = _pc_data.copy()
    _pc_bar["colloquial"] = _pc_bar["kuan"].map(KUAN_COLLOQUIAL).fillna(_pc_bar["kuan"])
    fig_pc = go.Figure()
    for _, r in _pc_bar.iterrows():
        fig_pc.add_trace(go.Bar(
            x=[r["per_capita"]],
            y=["1人あたり"],
            orientation="h",
            name=f'{r["kuan"]}（{r["colloquial"]}）',
            marker_color=kuan_color_map.get(r["kuan"], "#94a3b8"),
            hovertemplate=f'<b>{r["kuan"]}</b>（{r["colloquial"]}）<br>{r["per_capita"]:,.0f}円<extra></extra>',
        ))
    fig_pc.update_layout(
        barmode="stack",
        height=100,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=False,
    )
    st.plotly_chart(fig_pc, use_container_width=True, config={"displayModeBar": False})
    st.caption(f"人口 {POPULATION:,}人で計算。1人あたり合計 {per_capita_man:,.0f}万円")

    # ── 款別予算（横棒）──
    st.markdown('<div class="section-title">款別の予算額</div>', unsafe_allow_html=True)
    st.caption("予算を分野ごとに並べたもの。棒が長いほど多くのお金が使われます")
    chart_data = sum_data.sort_values("amount_current", ascending=False).copy()
    chart_data["label"] = chart_data["amount_current"].apply(lambda x: fmt_oku(x, short=True))
    chart_data["kuan_display"] = chart_data["kuan"].apply(kuan_with_colloquial)

    fig_bar = px.bar(
        chart_data, x="amount_current", y="kuan_display",
        orientation="h",
        color="kuan",
        color_discrete_map=kuan_color_map,
        text="label",
    )
    fig_bar.update_layout(
        height=max(350, len(chart_data) * 36),
        showlegend=False,
        margin=dict(l=0, r=60, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title="", categoryorder="total ascending"),
    )
    fig_bar.update_traces(
        textposition="outside",
        textfont_size=13,
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>%{text}<extra></extra>",
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # ── 構成比（ツリーマップ） ──
    st.markdown('<div class="section-title">構成比</div>', unsafe_allow_html=True)
    st.caption("全体を100%としたとき、各分野がどれくらいの割合かを面積で表示")
    tree_data = sum_data[["kuan", "amount_current"]].copy()
    tree_data["label"] = tree_data.apply(
        lambda r: f"{r['kuan']}<br>{fmt_oku(int(r['amount_current']))}", axis=1)
    fig_tree = px.treemap(
        tree_data, path=["kuan"], values="amount_current",
        color="kuan",
        color_discrete_map=kuan_color_map,
    )
    fig_tree.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig_tree.update_traces(
        textinfo="label+value+percent root",
        texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}",
        hovertemplate="<b>%{label}</b><br>%{value:,}千円<br>%{percentRoot:.1%}<extra></extra>",
        textfont_size=13,
    )
    st.plotly_chart(fig_tree, use_container_width=True, config={"displayModeBar": False})

    # ── 前年度との比較 ──
    st.markdown('<div class="section-title">前年度との増減</div>', unsafe_allow_html=True)
    st.caption("昨年と比べて増えた分野・減った分野。大きく変わった分野に注目")
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
        margin=dict(l=0, r=70, t=10, b=10),
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

    # ── 増減の主な要因（主要事業から自動生成） ──
    # major_projects.budget_category → expenditure.moku → kuan のマッピング構築
    _moku_kuan = expenditure[["kuan", "moku"]].drop_duplicates()
    _mp_diff = major_projects[major_projects["account_type"] == "一般会計"][
        ["budget_category", "project_name", "is_new", "amount_current", "amount_previous"]
    ].copy()
    _mp_diff["diff"] = _mp_diff["amount_current"] - _mp_diff["amount_previous"]
    # exactマッチ
    _mp_diff = _mp_diff.merge(
        _moku_kuan, left_on="budget_category", right_on="moku", how="left"
    )
    # マッチしなかった行は部分マッチで補完
    _unmatched = _mp_diff[_mp_diff["kuan"].isna()]
    for idx in _unmatched.index:
        cat = _mp_diff.loc[idx, "budget_category"][:4]
        partial = _moku_kuan[_moku_kuan["moku"].str.contains(cat)]
        if not partial.empty:
            _mp_diff.loc[idx, "kuan"] = partial["kuan"].iloc[0]

    # 増減が大きい款Top5について、要因となる事業を表示
    _big_kuan = comp_data[comp_data["diff"].abs() >= 10000].sort_values("diff", key=abs, ascending=False).head(5)
    if not _big_kuan.empty:
        annotations = []
        for _, bk in _big_kuan.iterrows():
            kname = bk["kuan"]
            kuan_mp = _mp_diff[_mp_diff["kuan"] == kname].copy()
            if kuan_mp.empty:
                continue
            top_movers = kuan_mp.sort_values("diff", key=abs, ascending=False).head(2)
            reasons = []
            for _, tm in top_movers.iterrows():
                d = int(tm["diff"])
                if abs(d) < 5000:
                    continue
                new_tag = "【新規】" if tm["is_new"] else ""
                reasons.append(f"{new_tag}{tm['project_name']}（{fmt_diff(d, short=True)}）")
            if reasons:
                direction = "増" if int(bk["diff"]) >= 0 else "減"
                annotations.append(
                    f"<b>{kname}</b>（{fmt_diff(int(bk['diff']), short=True)}）… {' / '.join(reasons)}"
                )
        if annotations:
            st.caption("増減の主な要因（主要事業より）")
            anno_html = '<div style="font-size:0.9rem; line-height:1.8">'
            for a in annotations:
                anno_html += f"・{a}<br>"
            anno_html += "</div>"
            st.markdown(anno_html, unsafe_allow_html=True)

    st.markdown("---")


# ═══════════════════════════════════════════════════════════
# タブ2: 財政構造（自主/依存 + 性質別 + サンキー図）
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown(f'<div class="section-title">歳入の構造 ── {tip("自主財源")} vs {tip("依存財源")}</div>', unsafe_allow_html=True)
    st.caption("町のお金がどこから来ているか。自力で集めたお金と国・県に頼るお金の比率")

    # 地方交付税依存度
    koufu_row = rev_summary[rev_summary["kuan"] == "地方交付税"]
    koufu_amt = int(koufu_row["amount_current"].iloc[0]) if not koufu_row.empty else 0
    koufu_ratio = safe_pct(koufu_amt, total_rev)

    st.markdown(f"""
    <div class="highlight-box">
        <strong>財政構造のポイント</strong><br>
        ・自主財源比率は<strong>{indep_ratio:.1f}%</strong>（ふるさと納税除くと<strong>{indep_adjusted_ratio:.1f}%</strong>）。依存財源が歳入の過半を占めます<br>
        ・地方交付税への依存度は<strong>{koufu_ratio:.1f}%</strong>（{fmt_oku(koufu_amt)}）<br>
        ・ふるさと納税（{fmt_oku(FURUSATO_REVENUE)}）が自主財源を大きく押し上げています
    </div>
    """, unsafe_allow_html=True)

    # 指標カード
    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">自主財源比率</div>
            <div class="indicator-value">{indep_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">{fmt_oku(indep_total)} / {fmt_oku(total_rev)}</div>
        </div>
        """, unsafe_allow_html=True)
    with rc2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">補正自主財源比率<br><span style="font-size:0.75rem">（ふるさと納税除く）</span></div>
            <div class="indicator-value">{indep_adjusted_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">{fmt_oku(indep_adjusted)} / {fmt_oku(total_rev)}</div>
        </div>
        """, unsafe_allow_html=True)
    with rc3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">{tip("地方交付税")}依存度</div>
            <div class="indicator-value">{koufu_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">{fmt_oku(koufu_amt)}</div>
        </div>
        """, unsafe_allow_html=True)

    # 自主/依存 ドーナツ
    rev_by_class = rev_summary.groupby("財源区分")["amount_current"].sum().reset_index()
    # ふるさと納税を分離した3区分版
    rev_3cat = pd.DataFrame([
        {"区分": "自主財源(税等)", "amount": indep_adjusted},
        {"区分": "ふるさと納税", "amount": furusato_amt},
        {"区分": "依存財源", "amount": dep_total},
    ])

    col_rev1, col_rev2 = st.columns(2)
    with col_rev1:
        st.markdown('<div class="section-subtitle">通常分類</div>', unsafe_allow_html=True)
        fig_rev2 = px.pie(
            rev_by_class, values="amount_current", names="財源区分",
            color="財源区分",
            color_discrete_map={"自主財源": "#22c55e", "依存財源": "#f97316"},
            hole=0.5,
        )
        fig_rev2.update_layout(
            height=360, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font_size=13),
        )
        fig_rev2.update_traces(
            textinfo="percent", textfont_size=14, textposition="inside",
            hovertemplate="<b>%{label}</b><br>%{percent}<br>%{value:,}千円<extra></extra>",
        )
        st.plotly_chart(fig_rev2, use_container_width=True, config={"displayModeBar": False})

    with col_rev2:
        st.markdown('<div class="section-subtitle">ふるさと納税を分離</div>', unsafe_allow_html=True)
        fig_rev3 = px.pie(
            rev_3cat, values="amount", names="区分",
            color="区分",
            color_discrete_map={
                "自主財源(税等)": "#22c55e",
                "ふるさと納税": "#2563eb",
                "依存財源": "#f97316",
            },
            hole=0.5,
        )
        fig_rev3.update_layout(
            height=360, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font_size=13),
        )
        fig_rev3.update_traces(
            textinfo="percent", textfont_size=14,
            textposition="inside",
            hovertemplate="<b>%{label}</b><br>%{percent}<br>%{value:,}千円<extra></extra>",
        )
        st.plotly_chart(fig_rev3, use_container_width=True, config={"displayModeBar": False})

    # ── 歳入内訳テーブル ──
    st.markdown('<div class="section-title">歳入の款別内訳</div>', unsafe_allow_html=True)
    st.caption("歳入を項目ごとに一覧表示。金額・前年比・構成比が確認できます")
    rev_table = rev_summary[["kuan", "amount_current", "amount_previous", "diff"]].copy()
    rev_table["財源区分"] = rev_summary["kuan"].apply(classify_revenue)
    rev_table["構成比"] = rev_table["amount_current"].apply(lambda x: f"{safe_pct(x, total_rev):.1f}%")
    rev_table = rev_table.rename(columns={
        "kuan": "款", "amount_current": "本年度(千円)",
        "amount_previous": "前年度(千円)", "diff": "増減(千円)",
    })
    rev_table = rev_table.sort_values("本年度(千円)", ascending=False)
    st.dataframe(rev_table, use_container_width=True, height=400)

    # ══════ 歳出の性質別分類 ══════
    st.markdown("---")
    st.markdown(f'<div class="section-title">歳出の{tip("性質別")}分類</div>', unsafe_allow_html=True)
    st.caption("お金の「使い方」で分けた分類。人件費・工事費など、何にお金が使われているか")

    # 指標カード（性質別データは全タブ共通で事前計算済み）
    nc1, nc2, nc3, nc4 = st.columns(4)
    with nc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">{tip("義務的経費")}比率</div>
            <div class="indicator-value clr-red">{obligatory_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">人件費+{tip("扶助費")}+{tip("公債費")}</div>
        </div>
        """, unsafe_allow_html=True)
    with nc2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">投資的経費比率</div>
            <div class="indicator-value clr-cyan">{investment_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">工事・備品・購入費等</div>
        </div>
        """, unsafe_allow_html=True)
    with nc3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">自主財源比率</div>
            <div class="indicator-value clr-green">{indep_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">ふるさと納税込み</div>
        </div>
        """, unsafe_allow_html=True)
    with nc4:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">自主財源比率<br><span style="font-size:0.7rem">（ふるさと納税除く）</span></div>
            <div class="indicator-value clr-muted">{indep_adjusted_ratio:.1f}<span style="font-size:1rem">%</span></div>
            <div class="indicator-sub">補正値</div>
        </div>
        """, unsafe_allow_html=True)

    # 性質別ツリーマップ（階層付き）
    nature_tree = nature_agg.copy()
    nature_tree["分類"] = nature_tree["性質"].apply(
        lambda x: "義務的経費" if x in obligatory_cats else ("投資的経費" if x == "投資的経費" else "その他経費")
    )
    fig_nature = px.treemap(
        nature_tree, path=["分類", "性質"], values="金額",
        color="性質",
        color_discrete_map=NATURE_COLORS,
    )
    fig_nature.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig_nature.update_traces(
        texttemplate="<b>%{label}</b><br>%{percentRoot:.1%}",
        hovertemplate="<b>%{label}</b><br>%{value:,}千円<br>%{percentRoot:.1%}<extra></extra>",
        textfont_size=12,
    )
    st.plotly_chart(fig_nature, use_container_width=True, config={"displayModeBar": False})

    # 性質別テーブル
    nature_table = nature_agg.copy()
    nature_table["構成比"] = nature_table["金額"].apply(lambda x: f"{safe_pct(x, nature_total):.1f}%")
    nature_table["金額表示"] = nature_table["金額"].apply(fmt_oku)
    nature_table["分類"] = nature_table["性質"].apply(
        lambda x: "義務的経費" if x in obligatory_cats else ("投資的経費" if x == "投資的経費" else "その他経費")
    )
    st.dataframe(
        nature_table[["分類", "性質", "金額表示", "構成比", "金額"]].rename(columns={"金額": "金額(千円)"}),
        use_container_width=True, height=350,
    )

    # ── お金の流れ（サンキー図）──
    st.markdown("---")
    st.markdown('<div class="section-title">お金の流れ（歳入→歳出）</div>', unsafe_allow_html=True)
    st.caption("左が収入源（どこからお金が来るか）、右が使い道（何にお金を使うか）。線の太さが金額の大きさを表します。")

    col_note1, col_note2 = st.columns(2)
    with col_note1:
        st.markdown("""
        <div class="highlight-box hl-blue">
        <strong>💰 特定財源とは？</strong><br>
        使い道があらかじめ決まっているお金。国・県からの補助金や町債（借入金）など、
        「この事業に使ってください」と用途が指定されている財源です。
        特定の事業にしか充てられないため、町の裁量では使い道を変えられません。
        </div>
        """, unsafe_allow_html=True)
    with col_note2:
        st.markdown("""
        <div class="highlight-box hl-green">
        <strong>🏛️ 一般財源とは？</strong><br>
        町が自由に使い道を決められるお金。町税や地方交付税が中心で、
        どの事業にいくら充てるかは町の判断に委ねられています。
        一般財源の割合が高い事業ほど、町の政策的な優先度が反映されていると言えます。
        </div>
        """, unsafe_allow_html=True)

    # -- ノード構築 --
    # 歳入側：主要カテゴリに集約
    rev_categories = {
        "町税": ["町税"],
        "地方交付税": ["地方交付税"],
        "ふるさと納税": ["寄附金"],
        "国・県支出金": ["国庫支出金", "県支出金"],
        "町債（借入）": ["町債"],
        "その他歳入": [
            "地方譲与税", "利子割交付金", "配当割交付金",
            "株式等譲渡所得割交付金", "法人事業税交付金",
            "地方消費税交付金", "環境性能割交付金",
            "地方特例交付金", "交通安全対策特別交付金",
            "分担金及び負担金", "使用料及び手数料",
            "財産収入", "繰入金", "繰越金", "諸収入",
        ],
    }

    rev_cat_amounts = {}
    for cat, kuans in rev_categories.items():
        amt = int(rev_summary[rev_summary["kuan"].isin(kuans)]["amount_current"].sum())
        if amt > 0:
            rev_cat_amounts[cat] = amt

    # 歳出側：summaryのsrc_*カラムを使って財源構成を取得
    exp_src = sum_exp[["kuan", "src_national", "src_bond", "src_other", "src_general"]].copy()
    exp_kuan_list = sum_exp.sort_values("amount_current", ascending=False)["kuan"].tolist()
    # 小さい款は集約
    exp_kuan_major = [k for k in exp_kuan_list if int(sum_exp[sum_exp["kuan"] == k]["amount_current"].iloc[0]) >= 50000]
    exp_kuan_minor = [k for k in exp_kuan_list if k not in exp_kuan_major]

    # ノードリスト作成
    source_nodes = list(rev_cat_amounts.keys())
    middle_nodes = ["一般財源", "特定財源"]
    if exp_kuan_minor:
        target_nodes = exp_kuan_major + ["その他歳出"]
    else:
        target_nodes = exp_kuan_major

    all_nodes = source_nodes + middle_nodes + target_nodes
    node_idx = {n: i for i, n in enumerate(all_nodes)}

    # ノード色
    node_colors = []
    rev_node_colors = {
        "町税": "#22c55e", "地方交付税": "#f97316", "ふるさと納税": "#2563eb",
        "国・県支出金": "#a855f7", "町債（借入）": "#f43f5e", "その他歳入": "#94a3b8",
    }
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

    # -- リンク構築 --
    link_source = []
    link_target = []
    link_value = []
    link_color = []

    # 歳出側の財源構成（これが正）
    total_src_general = int(sum_exp["src_general"].sum())
    total_src_specific = int(sum_exp["src_national"].sum()) + int(sum_exp["src_bond"].sum()) + int(sum_exp["src_other"].sum())

    # 歳入カテゴリ → 一般財源/特定財源
    # 明確に分類できるもの
    fixed_general = {"町税", "地方交付税"}  # → 一般財源
    fixed_specific = {"国・県支出金", "町債（借入）", "ふるさと納税"}  # → 特定財源

    fixed_specific_total = sum(v for k, v in rev_cat_amounts.items() if k in fixed_specific)
    fixed_general_total = sum(v for k, v in rev_cat_amounts.items() if k in fixed_general)

    # 「その他歳入」は一般/特定の両方を含む（基金繰入金など）
    # 歳出側の合計に合うよう按分する
    other_total = rev_cat_amounts.get("その他歳入", 0)
    other_to_specific = max(0, total_src_specific - fixed_specific_total)
    other_to_general = max(0, other_total - other_to_specific)

    for cat, amt in rev_cat_amounts.items():
        if cat in fixed_general:
            link_source.append(node_idx[cat])
            link_target.append(node_idx["一般財源"])
            link_value.append(amt)
            link_color.append("rgba(148, 163, 184, 0.3)")
        elif cat in fixed_specific:
            link_source.append(node_idx[cat])
            link_target.append(node_idx["特定財源"])
            link_value.append(amt)
            link_color.append("rgba(37, 99, 235, 0.2)")
        elif cat == "その他歳入":
            # 一般財源分（財政調整基金繰入金、交付金等）
            if other_to_general > 0:
                link_source.append(node_idx[cat])
                link_target.append(node_idx["一般財源"])
                link_value.append(other_to_general)
                link_color.append("rgba(148, 163, 184, 0.3)")
            # 特定財源分（ふるさと基金繰入金、下水道基金等）
            if other_to_specific > 0:
                link_source.append(node_idx[cat])
                link_target.append(node_idx["特定財源"])
                link_value.append(other_to_specific)
                link_color.append("rgba(37, 99, 235, 0.2)")

    # 一般財源/特定財源 → 歳出の款
    for _, row in exp_src.iterrows():
        kuan = row["kuan"]
        if kuan in exp_kuan_major:
            target = kuan
        else:
            target = "その他歳出"

        # 一般財源 → 款
        gen_val = int(row["src_general"]) if pd.notna(row["src_general"]) else 0
        if gen_val > 0:
            link_source.append(node_idx["一般財源"])
            link_target.append(node_idx[target])
            link_value.append(gen_val)
            link_color.append("rgba(148, 163, 184, 0.25)")

        # 特定財源 → 款
        spec_val = sum(int(row[c]) if pd.notna(row[c]) else 0 for c in ["src_national", "src_bond", "src_other"])
        if spec_val > 0:
            link_source.append(node_idx["特定財源"])
            link_target.append(node_idx[target])
            link_value.append(spec_val)
            link_color.append("rgba(37, 99, 235, 0.15)")

    fig_sankey = go.Figure(go.Sankey(
        arrangement="snap",
        textfont=dict(size=15, color="#1e293b", family="sans-serif"),
        node=dict(
            pad=25,
            thickness=24,
            line=dict(color="white", width=2),
            label=all_nodes,
            color=node_colors,
            hovertemplate="%{label}<br>%{value:,}千円<extra></extra>",
        ),
        link=dict(
            source=link_source,
            target=link_target,
            value=link_value,
            color=link_color,
            hovertemplate="%{source.label} → %{target.label}<br>%{value:,}千円<extra></extra>",
        ),
    ))
    fig_sankey.update_layout(
        height=500,
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(size=15, color="#1e293b", family="sans-serif"),
    )
    st.plotly_chart(fig_sankey, use_container_width=True, config={"displayModeBar": False})

    # サンキー図の検証情報
    st.caption(f"歳入合計: {fmt_oku(total_rev)} / 歳出合計: {fmt_oku(total_exp)}")


# ═══════════════════════════════════════════════════════════
# タブ3: 深掘り分析（一般財源充当率・町債・人件費）
# ═══════════════════════════════════════════════════════════
with tab3:
    # 深掘り分析ハイライト用の事前計算
    _gen_tmp = sum_exp[["kuan", "amount_current", "src_general"]].copy()
    _gen_tmp["ratio"] = _gen_tmp.apply(lambda r: safe_pct(r["src_general"], r["amount_current"]), axis=1)
    _gen_high = _gen_tmp[(_gen_tmp["ratio"] >= 80) & (_gen_tmp["amount_current"] >= 100_000)].sort_values("ratio", ascending=False)
    _gen_low = _gen_tmp[_gen_tmp["ratio"] <= 40].sort_values("ratio")
    _bond_total = int(sum_exp["src_bond"].sum())
    _national_total = int(sum_exp["src_national"].sum())
    _high_names = "・".join(_gen_high["kuan"].head(3).tolist()) if not _gen_high.empty else "なし"
    _low_names = "・".join(_gen_low["kuan"].head(3).tolist()) if not _gen_low.empty else "なし"

    st.markdown(f"""
    <div class="highlight-box">
        <strong>深掘り分析のポイント</strong><br>
        ・町の持ち出しが大きい分野: <strong>{_high_names}</strong>（充当率80%以上・予算1億円以上）<br>
        ・国県の補助を活用している分野: <strong>{_low_names}</strong>（充当率40%以下）<br>
        ・町債（借入）は全体で<strong>{fmt_oku(_bond_total)}</strong>、国・県支出金は<strong>{fmt_oku(_national_total)}</strong>
    </div>
    """, unsafe_allow_html=True)

    # ── 財源の内訳（款別積み上げ棒） ──
    st.markdown('<div class="section-title">財源の内訳（どこからお金が来ているか）</div>', unsafe_allow_html=True)
    st.caption("各分野の予算が、どの財源で賄われているかを示します。色の構成で財源の依存度が一目でわかります。")
    src_data = sum_exp[["kuan", "src_national", "src_bond", "src_other", "src_general"]].copy()
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

    # ── 款別の一般財源充当率 ──
    st.markdown(f'<div class="section-title">款別の{tip("一般財源充当率")}</div>', unsafe_allow_html=True)
    st.caption("各款の予算のうち、町の一般財源（税・交付税等）で賄っている割合。バーの長さが充当率、色の濃さが予算規模を表します。")

    gen_ratio = sum_exp[["kuan", "amount_current", "src_general"]].copy()
    gen_ratio["一般財源充当率"] = gen_ratio.apply(
        lambda r: round(safe_pct(r["src_general"], r["amount_current"]), 1), axis=1
    )
    gen_ratio = gen_ratio.sort_values("一般財源充当率", ascending=True)
    gen_ratio["label"] = gen_ratio["一般財源充当率"].apply(lambda x: f"{x:.1f}%")
    gen_ratio["金額表示"] = gen_ratio.apply(
        lambda r: f"{r['src_general']:,.0f}千円 / {r['amount_current']:,.0f}千円", axis=1
    )

    # 色の濃さ＝予算規模（金額が大きい款ほど濃く、小さい款は自然と薄く）
    amounts = gen_ratio["amount_current"].values.astype(float)
    log_amounts = np.log1p(amounts)
    a_min, a_max = log_amounts.min(), log_amounts.max()
    if a_max > a_min:
        norm = (log_amounts - a_min) / (a_max - a_min)
    else:
        norm = np.ones_like(log_amounts) * 0.5
    # 落ち着いたスレートブルー系 — 薄い(0.15)→濃い(0.85)
    colors = [f"rgba(51,65,85,{0.15 + 0.70 * n:.2f})" for n in norm]

    fig_gen = go.Figure()
    fig_gen.add_trace(go.Bar(
        x=gen_ratio["一般財源充当率"].values,
        y=gen_ratio["kuan"].values,
        orientation="h",
        text=gen_ratio["label"].values,
        marker_color=colors,
        customdata=gen_ratio["金額表示"].values,
        hovertemplate="<b>%{y}</b><br>一般財源充当率: %{text}<br>%{customdata}<extra></extra>",
    ))
    fig_gen.update_layout(
        height=max(300, len(gen_ratio) * 36),
        margin=dict(l=0, r=60, t=10, b=10),
        xaxis=dict(visible=False, range=[0, 115]),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_gen.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_gen, use_container_width=True, config={"displayModeBar": False})

    # ── 人件費の全体像 ──
    st.markdown("---")
    st.markdown('<div class="section-title">人件費の全体像 ── どこに人がいるか</div>', unsafe_allow_html=True)
    st.caption("報酬・給料・職員手当等・共済費の合計を款別に集計しています。")

    personnel_setsu = ["報酬", "給料", "職員手当等", "共済費"]
    exp_personnel = expenditure[expenditure["setsu"].isin(personnel_setsu)].copy()
    personnel_by_kuan = exp_personnel.groupby("kuan")["setsu_amount"].sum().reset_index()
    personnel_by_kuan.columns = ["kuan", "人件費"]
    personnel_by_kuan = personnel_by_kuan.sort_values("人件費", ascending=False)
    personnel_total = int(personnel_by_kuan["人件費"].sum())

    pc1, pc2 = st.columns(2)
    with pc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">人件費合計</div>
            <div class="indicator-value">{fmt_oku(personnel_total)}</div>
            <div class="indicator-sub">歳出全体の{personnel_total/total_exp*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with pc2:
        per_capita_personnel = personnel_total * 1000 / POPULATION / 10000
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">町民1人あたり人件費</div>
            <div class="indicator-value">{per_capita_personnel:,.1f}<span style="font-size:1rem">万円</span></div>
        </div>
        """, unsafe_allow_html=True)

    personnel_chart = personnel_by_kuan.sort_values("人件費", ascending=True).copy()
    personnel_chart["label"] = personnel_chart["人件費"].apply(lambda x: fmt_oku(x, short=True))
    personnel_chart["kuan_display"] = personnel_chart["kuan"].apply(kuan_with_colloquial)

    fig_personnel = px.bar(
        personnel_chart, x="人件費", y="kuan_display", orientation="h",
        text="label",
        color_discrete_sequence=["#2563eb"],
    )
    fig_personnel.update_layout(
        height=max(300, len(personnel_chart) * 34),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_personnel.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_personnel, use_container_width=True, config={"displayModeBar": False})

    with st.expander("人件費の内訳（節別）"):
        personnel_by_setsu = exp_personnel.groupby("setsu")["setsu_amount"].sum().reset_index()
        personnel_by_setsu.columns = ["節", "金額"]
        personnel_by_setsu["金額表示"] = personnel_by_setsu["金額"].apply(fmt_oku)
        personnel_by_setsu["構成比"] = (personnel_by_setsu["金額"] / personnel_total * 100).round(1).astype(str) + "%"
        personnel_by_setsu = personnel_by_setsu.sort_values("金額", ascending=False)
        st.dataframe(
            personnel_by_setsu[["節", "金額表示", "構成比", "金額"]].rename(columns={"金額": "金額(千円)"}),
            use_container_width=True, hide_index=True, height=400,
        )

    # ── 町債（借金）の中身 ──
    st.markdown("---")
    st.markdown('<div class="section-title">町債（借金）の中身 ── 何のために借りているか</div>', unsafe_allow_html=True)
    st.caption("地方債は将来の住民も利用する施設等のために借り入れる資金です。何に充てているかを示します。")

    bond_data = sum_exp[sum_exp["src_bond"] > 0][["kuan", "src_bond"]].copy()
    bond_total = int(bond_data["src_bond"].sum())

    # 歳入側の町債
    rev_bond = int(sum_rev[sum_rev["kuan"] == "町債"]["amount_current"].iloc[0]) if not sum_rev[sum_rev["kuan"] == "町債"].empty else 0

    bc1, bc2 = st.columns(2)
    with bc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">新規借入額（町債）</div>
            <div class="indicator-value clr-orange">{fmt_oku(rev_bond)}</div>
            <div class="indicator-sub">歳入に計上</div>
        </div>
        """, unsafe_allow_html=True)
    with bc2:
        kouhi = int(sum_exp[sum_exp["kuan"] == "公債費"]["amount_current"].iloc[0]) if not sum_exp[sum_exp["kuan"] == "公債費"].empty else 0
        balance = rev_bond - kouhi
        balance_color = "#f43f5e" if balance > 0 else "#22c55e"
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">返済額（公債費）</div>
            <div class="indicator-value">{fmt_oku(kouhi)}</div>
            <div class="indicator-sub" style="color:{balance_color}">差引 {fmt_diff(balance)}（{'借入超過' if balance > 0 else '返済超過'}）</div>
        </div>
        """, unsafe_allow_html=True)

    bond_chart = bond_data.sort_values("src_bond", ascending=True).copy()
    bond_chart["label"] = bond_chart["src_bond"].apply(lambda x: fmt_oku(x, short=True))
    bond_chart["kuan_display"] = bond_chart["kuan"].apply(kuan_with_colloquial)

    fig_bond = px.bar(
        bond_chart, x="src_bond", y="kuan_display", orientation="h",
        text="label",
        color_discrete_sequence=["#f97316"],
    )
    fig_bond.update_layout(
        height=max(200, len(bond_chart) * 40),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_bond.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_bond, use_container_width=True, config={"displayModeBar": False})

    with st.expander("町債の主な充当先（主要事業より）"):
        bond_projects = major_projects[
            (major_projects["account_type"] == "一般会計") & (major_projects["src_bond"] > 0)
        ].sort_values("src_bond", ascending=False)
        if not bond_projects.empty:
            bp_show = bond_projects[["project_name", "department", "src_bond", "amount_current"]].rename(columns={
                "project_name": "事業名", "department": "担当課",
                "src_bond": "地方債(千円)", "amount_current": "事業費(千円)",
            })
            st.dataframe(bp_show, use_container_width=True, hide_index=True, height=400)


# ═══════════════════════════════════════════════════════════
# タブ4: 主要事業
# ═══════════════════════════════════════════════════════════
with tab4:
    mp = major_projects[major_projects["account_type"] == "一般会計"].copy()
    mp_all = major_projects.copy()

    st.markdown('<div class="section-title">主要事業の概要</div>', unsafe_allow_html=True)
    st.caption("町が特に重要と位置づけている事業の一覧と全体像")

    mp_count = len(mp)
    mp_new_count = int(mp["is_new"].sum())
    mp_total = int(mp["amount_current"].sum())
    if not mp.empty:
        _mp_top = mp.sort_values("amount_current", ascending=False).iloc[0]
        _mp_new_label = "【新規】" if _mp_top["is_new"] else ""
        st.markdown(f"""
        <div class="highlight-box">
            <strong>主要事業のポイント</strong><br>
            ・一般会計で<strong>{mp_count}事業</strong>（うち新規<strong>{mp_new_count}件</strong>）、総額<strong>{fmt_oku(mp_total)}</strong><br>
            ・最大事業: <strong>{_mp_top['project_name']}</strong>（{fmt_oku(int(_mp_top['amount_current']))}）{_mp_new_label}<br>
            ・ふるさと納税基金を活用した事業が多数含まれています
        </div>
        """, unsafe_allow_html=True)

    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">一般会計 主要事業数</div>
            <div class="indicator-value">{mp_count}<span style="font-size:1rem">件</span></div>
        </div>
        """, unsafe_allow_html=True)
    with mc2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">うち新規事業</div>
            <div class="indicator-value clr-blue">{mp_new_count}<span style="font-size:1rem">件</span></div>
        </div>
        """, unsafe_allow_html=True)
    with mc3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">主要事業 合計額</div>
            <div class="indicator-value">{fmt_oku(mp_total)}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── 新規事業一覧 ──
    st.markdown('<div class="section-title">新規事業</div>', unsafe_allow_html=True)
    st.caption("令和8年度に新たに予算化された事業です。")

    mp_new = mp[mp["is_new"] == 1].sort_values("amount_current", ascending=False).copy()
    mp_new["金額"] = mp_new["amount_current"].apply(fmt_oku)

    for _, row in mp_new.iterrows():
        amt_str = fmt_oku(int(row["amount_current"]))
        desc = row["description"] if pd.notna(row["description"]) else ""
        desc_short = desc[:120] + "…" if len(desc) > 120 else desc
        st.markdown(
            f'<div class="highlight-box">'
            f'<strong>{row["project_name"]}</strong>'
            f'<span style="float:right;color:#2563eb;font-weight:700">{amt_str}</span><br>'
            f'<span style="font-size:0.85rem;color:#64748b">{row["department"]} / {row["budget_category"]}</span><br>'
            f'{desc_short}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 担当課別集計 ──
    st.markdown('<div class="section-title">担当課別の事業数・予算額</div>', unsafe_allow_html=True)
    st.caption("どの課がどれくらいの事業と予算を担当しているか")

    dept_agg = mp.groupby("department").agg(
        事業数=("id", "count"),
        新規=("is_new", "sum"),
        予算額=("amount_current", "sum"),
    ).reset_index().rename(columns={"department": "担当課"})
    dept_agg["新規"] = dept_agg["新規"].astype(int)
    dept_agg = dept_agg.sort_values("予算額", ascending=False)

    fig_dept = px.bar(
        dept_agg.sort_values("予算額", ascending=True),
        x="予算額", y="担当課", orientation="h",
        text=dept_agg.sort_values("予算額", ascending=True)["予算額"].apply(lambda x: fmt_oku(x, short=True)),
        color_discrete_sequence=["#2563eb"],
    )
    fig_dept.update_layout(
        height=max(300, len(dept_agg) * 34),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_dept.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_dept, use_container_width=True, config={"displayModeBar": False})

    # 担当課別テーブル
    dept_table = dept_agg.copy()
    dept_table["予算額表示"] = dept_table["予算額"].apply(fmt_oku)
    st.dataframe(
        dept_table[["担当課", "事業数", "新規", "予算額表示", "予算額"]].rename(columns={"予算額": "予算額(千円)"}),
        use_container_width=True, height=400, hide_index=True,
    )

    # ── 全事業一覧 ──
    st.markdown('<div class="section-title">全事業一覧</div>', unsafe_allow_html=True)
    st.caption("担当課や新規事業で絞り込めます。列の見出しクリックで並べ替え可能")

    # フィルタ
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        dept_filter = st.selectbox(
            "担当課で絞り込み",
            ["すべて"] + sorted(mp["department"].unique().tolist()),
            key="mp_dept_filter",
        )
    with filter_col2:
        new_filter = st.selectbox(
            "新規/継続",
            ["すべて", "新規のみ", "継続のみ"],
            key="mp_new_filter",
        )

    mp_filtered = mp.copy()
    if dept_filter != "すべて":
        mp_filtered = mp_filtered[mp_filtered["department"] == dept_filter]
    if new_filter == "新規のみ":
        mp_filtered = mp_filtered[mp_filtered["is_new"] == 1]
    elif new_filter == "継続のみ":
        mp_filtered = mp_filtered[mp_filtered["is_new"] == 0]

    mp_show = mp_filtered[[
        "project_name", "department", "budget_category",
        "amount_current", "amount_previous", "is_new", "description",
    ]].rename(columns={
        "project_name": "事業名", "department": "担当課",
        "budget_category": "予算科目",
        "amount_current": "本年度(千円)", "amount_previous": "前年度(千円)",
        "is_new": "新規", "description": "説明",
    }).sort_values("本年度(千円)", ascending=False)
    mp_show["新規"] = mp_show["新規"].map({1: "★", 0: ""})

    st.dataframe(mp_show, use_container_width=True, height=500, hide_index=True)

    mp_csv = mp_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSV出力", mp_csv, "major_projects.csv", "text/csv", key="mp_csv")



# ═══════════════════════════════════════════════════════════
# タブ5: ふるさと納税（使いみち + テーマ + シミュレーション）
# ═══════════════════════════════════════════════════════════
with tab5:
    mp_ft = major_projects[major_projects["account_type"] == "一般会計"].copy()

    _ft_pct_of_rev = safe_pct(FURUSATO_REVENUE, total_rev)
    _ft_projects_count = len(mp_ft[mp_ft["furusato_amount"] > 0])
    st.markdown(f"""
    <div class="highlight-box">
        <strong>ふるさと納税のポイント</strong><br>
        ・寄附金収入は<strong>{fmt_oku(FURUSATO_REVENUE)}</strong>で歳入全体の<strong>{_ft_pct_of_rev:.1f}%</strong>を占めます<br>
        ・基金を活用した事業は<strong>{_ft_projects_count}件</strong>。町の幅広い分野に充当されています<br>
        ・下部のシミュレーションで「もしふるさと納税がなかったら？」を体験できます
    </div>
    """, unsafe_allow_html=True)

    # ── 使いみちマップ ──
    st.markdown('<div class="section-title">ふるさと納税の使いみち</div>', unsafe_allow_html=True)
    st.caption("ふるさと応援寄附金基金からの繰入金が充当されている事業の一覧です。寄附金がどう使われているかを示します。")

    mp_furusato = mp_ft[mp_ft["furusato_amount"] > 0].copy()
    mp_fund = mp_furusato[mp_furusato["project_name"] == "ふるさと応援寄附金基金積立金"]
    mp_ops = mp_furusato[mp_furusato["project_name"] == "ふるさと応援寄附金事業"]
    mp_projects_ft = mp_furusato[
        ~mp_furusato["project_name"].isin(["ふるさと応援寄附金基金積立金", "ふるさと応援寄附金事業"])
    ].sort_values("furusato_amount", ascending=False)

    fund_amt = int(mp_fund["furusato_amount"].sum()) if not mp_fund.empty else 0
    ops_amt = int(mp_ops["furusato_amount"].sum()) if not mp_ops.empty else 0
    projects_amt = int(mp_projects_ft["furusato_amount"].sum())

    fu1, fu2, fu3 = st.columns(3)
    with fu1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">基金積立</div>
            <div class="indicator-value">{fmt_oku(fund_amt)}</div>
            <div class="indicator-sub">将来の事業のための貯蓄</div>
        </div>
        """, unsafe_allow_html=True)
    with fu2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">運営コスト</div>
            <div class="indicator-value clr-red">{fmt_oku(ops_amt)}</div>
            <div class="indicator-sub">返礼品・広告・事務費</div>
        </div>
        """, unsafe_allow_html=True)
    with fu3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">事業への充当</div>
            <div class="indicator-value clr-green">{fmt_oku(projects_amt)}</div>
            <div class="indicator-sub">{len(mp_projects_ft)}事業に活用</div>
        </div>
        """, unsafe_allow_html=True)

    # テーマ分類
    THEME_MAP = {
        "子育て・教育": [
            "結婚祝金", "誕生祝金", "入学祝金", "卒業祝金",
            "障害児通所支援給付費", "母子保健事業委託料",
            "小学校補助教材支給事業（消耗品費）", "中学校補助教材支給事業（消耗品費）",
            "小学校高度情報教育用備品購入事業", "中学校高度情報教育用備品購入事業",
            "学校施設整備改修事業",
        ],
        "健康・医療": [
            "各種健（検）診委託料", "定期予防接種委託料",
        ],
        "農林水産業": [
            "鳥獣被害防止総合対策交付金事業", "有害鳥獣駆除対策費補助金",
            "有害鳥獣被害防止対策費補助金", "親元就農給付金",
            "さが園芸888整備支援事業費補助金", "農地基盤整備事業費補助金",
            "森林整備担い手育成基金助成事業費補助金", "森林環境保全直接支援事業委託料",
            "漁業従事者事業継続支援給付金",
        ],
        "インフラ・環境": [
            "交通安全施設整備事業", "町道維持補修事業",
            "家庭用合併処理浄化槽設置整備事業費補助金",
            "防災ハザードマップ更新委託料",
        ],
        "交通・移住": [
            "コミュニティバス運営事業", "タクシー運営事業",
            "移住定住促進事業補助金",
        ],
        "観光・商工": [
            "観光客誘客事業補助金",
        ],
    }

    project_to_theme = {}
    for theme, names in THEME_MAP.items():
        for n in names:
            project_to_theme[n] = theme

    mp_projects_ft["テーマ"] = mp_projects_ft["project_name"].map(project_to_theme).fillna("その他")

    theme_agg = mp_projects_ft.groupby("テーマ")["furusato_amount"].sum().reset_index()
    theme_agg.columns = ["テーマ", "金額"]
    theme_agg = theme_agg.sort_values("金額", ascending=False)

    theme_colors = {
        "子育て・教育": "#2563eb",
        "健康・医療": "#22c55e",
        "農林水産業": "#f97316",
        "インフラ・環境": "#06b6d4",
        "交通・移住": "#a855f7",
        "観光・商工": "#ec4899",
        "その他": "#94a3b8",
    }

    col_fu1, col_fu2 = st.columns([1, 1])
    with col_fu1:
        st.markdown('<div class="section-subtitle">寄附金の全体構成</div>', unsafe_allow_html=True)
        overview_data = pd.DataFrame([
            {"区分": "基金積立", "金額": fund_amt},
            {"区分": "運営コスト", "金額": ops_amt},
            {"区分": "事業充当", "金額": projects_amt},
        ])
        fig_fu_overview = px.pie(
            overview_data, values="金額", names="区分",
            color="区分",
            color_discrete_map={"基金積立": "#94a3b8", "運営コスト": "#f43f5e", "事業充当": "#22c55e"},
            hole=0.5,
        )
        fig_fu_overview.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
        fig_fu_overview.update_traces(
            textinfo="label+percent", textfont_size=12,
            hovertemplate="<b>%{label}</b><br>%{percent}<br>%{value:,}千円<extra></extra>",
        )
        st.plotly_chart(fig_fu_overview, use_container_width=True, config={"displayModeBar": False})

    with col_fu2:
        st.markdown('<div class="section-subtitle">事業充当の分野別内訳</div>', unsafe_allow_html=True)
        theme_bar = theme_agg.sort_values("金額", ascending=True).copy()
        theme_bar["label"] = theme_bar["金額"].apply(lambda x: fmt_oku(x, short=True))
        fig_fu_theme = px.bar(
            theme_bar, x="金額", y="テーマ", orientation="h",
            color="テーマ",
            color_discrete_map=theme_colors,
            text="label",
        )
        fig_fu_theme.update_layout(
            height=max(250, len(theme_bar) * 40),
            margin=dict(l=10, r=50, t=10, b=10),
            showlegend=False,
            xaxis=dict(visible=False),
            yaxis=dict(title=""),
        )
        fig_fu_theme.update_traces(
            textposition="outside", textfont_size=12, cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>%{x:,}千円<extra></extra>",
        )
        st.plotly_chart(fig_fu_theme, use_container_width=True, config={"displayModeBar": False})

    # 事業別の充当額（横棒）
    st.markdown('<div class="section-subtitle">事業別のふるさと納税充当額</div>', unsafe_allow_html=True)
    mp_proj_chart = mp_projects_ft.head(20).sort_values("furusato_amount", ascending=True).copy()
    mp_proj_chart["label"] = mp_proj_chart["furusato_amount"].apply(lambda x: fmt_oku(x, short=True))

    fig_fu_bar = px.bar(
        mp_proj_chart, x="furusato_amount", y="project_name", orientation="h",
        color="テーマ",
        color_discrete_map=theme_colors,
        text="label",
    )
    fig_fu_bar.update_layout(
        height=max(350, len(mp_proj_chart) * 30),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font_size=12),
    )
    fig_fu_bar.update_traces(
        textposition="outside", textfont_size=11,
        cliponaxis=False,
    )
    st.plotly_chart(fig_fu_bar, use_container_width=True, config={"displayModeBar": False})

    # ── テーマ別分類 ──
    st.markdown("---")
    st.markdown('<div class="section-title">主要事業のテーマ別分類</div>', unsafe_allow_html=True)
    st.caption("主要事業を政策テーマで横断的に分類しています。")

    mp_themed = mp_ft.copy()
    mp_themed["テーマ"] = mp_themed["project_name"].map(project_to_theme).fillna("その他")

    all_theme_agg = mp_themed.groupby("テーマ").agg(
        事業数=("id", "count"),
        新規=("is_new", "sum"),
        予算額=("amount_current", "sum"),
    ).reset_index()
    all_theme_agg["新規"] = all_theme_agg["新規"].astype(int)
    all_theme_agg = all_theme_agg.sort_values("予算額", ascending=False)

    fig_theme = px.bar(
        all_theme_agg.sort_values("予算額", ascending=True),
        x="予算額", y="テーマ", orientation="h",
        color="テーマ",
        color_discrete_map=theme_colors,
        text=all_theme_agg.sort_values("予算額", ascending=True)["予算額"].apply(lambda x: fmt_oku(x, short=True)),
    )
    fig_theme.update_layout(
        height=max(250, len(all_theme_agg) * 40),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_theme.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_theme, use_container_width=True, config={"displayModeBar": False})

    theme_table = all_theme_agg.copy()
    theme_table["予算額表示"] = theme_table["予算額"].apply(fmt_oku)
    st.dataframe(
        theme_table[["テーマ", "事業数", "新規", "予算額表示", "予算額"]].rename(columns={"予算額": "予算額(千円)"}),
        use_container_width=True, hide_index=True, height=400,
    )

    # ── もしもシミュレーション ──
    st.markdown("---")
    st.markdown('<div class="section-title">もしふるさと納税がなかったら？</div>', unsafe_allow_html=True)
    st.caption("ふるさと納税（寄附金）の規模を変えた場合、太良町の財政がどう変わるかをシミュレーションします。")

    furusato_rev = FURUSATO_REVENUE
    furusato_cost_items = FURUSATO_COST_ITEMS
    furusato_cost_total = sum(furusato_cost_items.values())
    furusato_fund_sim = FURUSATO_FUND_SIM
    furusato_net = furusato_rev - furusato_cost_total

    st.markdown('<div class="section-subtitle">現状（令和8年度）</div>', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">寄附金収入</div>
            <div class="indicator-value clr-blue">{fmt_oku(furusato_rev)}</div>
        </div>
        """, unsafe_allow_html=True)
    with fc2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">運営コスト</div>
            <div class="indicator-value clr-red">{fmt_oku(furusato_cost_total)}</div>
            <div class="indicator-sub">コスト率 {safe_pct(furusato_cost_total, furusato_rev):.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with fc3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">実質収入</div>
            <div class="indicator-value clr-green">{fmt_oku(furusato_net)}</div>
            <div class="indicator-sub">寄附金 − 運営コスト</div>
        </div>
        """, unsafe_allow_html=True)

    with st.expander("運営コストの内訳"):
        cost_df = pd.DataFrame([
            {"項目": k, "金額(千円)": v, "金額": fmt_oku(v)}
            for k, v in furusato_cost_items.items()
        ])
        cost_df = cost_df.sort_values("金額(千円)", ascending=False)
        st.dataframe(cost_df[["項目", "金額", "金額(千円)"]], use_container_width=True, hide_index=True, height=400)
        st.caption("予算書の説明欄から「ふるさと応援寄附金」関連の費目を抽出・推計しています。実際のコストと異なる場合があります。")

    st.markdown("---")

    st.markdown('<div class="section-subtitle">シミュレーション</div>', unsafe_allow_html=True)
    sim_pct = st.slider(
        "ふるさと納税の規模（現状比）",
        min_value=0, max_value=200, value=100, step=10,
        format="%d%%",
        help="0%=ふるさと納税がゼロ、100%=現状維持、200%=2倍",
    )

    sim_rev = int(furusato_rev * sim_pct / 100)
    sim_cost = int(furusato_cost_total * sim_pct / 100)
    sim_net = sim_rev - sim_cost
    sim_fund = int(furusato_fund_sim * sim_pct / 100)

    sim_total_rev = total_rev - furusato_rev + sim_rev
    sim_total_exp = total_exp - furusato_cost_total - furusato_fund_sim + sim_cost + sim_fund

    indep_base = int(sum_rev[sum_rev["kuan"].isin(INDEPENDENT_REVENUE)]["amount_current"].sum())
    sim_indep = indep_base - furusato_rev + sim_rev
    sim_indep_ratio = sim_indep / sim_total_rev * 100
    sim_indep_ex_ratio = (sim_indep - sim_rev) / sim_total_rev * 100
    sim_per_capita = sim_total_exp * 1000 / POPULATION / 10000

    st.markdown(f"**ふるさと納税が{'ゼロ' if sim_pct == 0 else f'現状の{sim_pct}%'}の場合**")

    sc1, sc2, sc3 = st.columns(3)
    with sc1:
        rev_diff_sim = sim_total_rev - total_rev
        rev_color = "#22c55e" if rev_diff_sim >= 0 else "#f43f5e"
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">歳入総額</div>
            <div class="indicator-value">{sim_total_rev/100000:,.1f}<span style="font-size:0.9rem">億円</span></div>
            <div class="indicator-sub" style="color:{rev_color}">現状比 {fmt_diff(rev_diff_sim)}</div>
        </div>
        """, unsafe_allow_html=True)
    with sc2:
        exp_diff_sim = sim_total_exp - total_exp
        exp_color = "#22c55e" if exp_diff_sim >= 0 else "#f43f5e"
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">歳出規模</div>
            <div class="indicator-value">{sim_total_exp/100000:,.1f}<span style="font-size:0.9rem">億円</span></div>
            <div class="indicator-sub" style="color:{exp_color}">現状比 {fmt_diff(exp_diff_sim)}</div>
        </div>
        """, unsafe_allow_html=True)
    with sc3:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">町民1人あたり</div>
            <div class="indicator-value">{sim_per_capita:,.0f}<span style="font-size:0.9rem">万円</span></div>
            <div class="indicator-sub">現状 {per_capita_man:,.0f}万円</div>
        </div>
        """, unsafe_allow_html=True)

    sd1, sd2 = st.columns(2)
    with sd1:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">自主財源比率</div>
            <div class="indicator-value">{sim_indep_ratio:.1f}<span style="font-size:0.9rem">%</span></div>
            <div class="indicator-sub">現状 {indep_total/total_rev*100:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with sd2:
        st.markdown(f"""
        <div class="indicator-card">
            <div class="indicator-label">自主財源比率（ふるさと納税除く）</div>
            <div class="indicator-value">{sim_indep_ex_ratio:.1f}<span style="font-size:0.9rem">%</span></div>
            <div class="indicator-sub">この値はふるさと納税の規模に依らない町の実力値</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">現状との比較</div>', unsafe_allow_html=True)
    st.caption("スライダーで設定した金額と現状を並べて比較")
    compare_items = pd.DataFrame([
        {"指標": "歳入総額", "現状": total_rev, "シミュレーション": sim_total_rev},
        {"指標": "歳出規模", "現状": total_exp, "シミュレーション": sim_total_exp},
        {"指標": "ふるさと納税収入", "現状": furusato_rev, "シミュレーション": sim_rev},
        {"指標": "ふるさと納税コスト", "現状": furusato_cost_total, "シミュレーション": sim_cost},
        {"指標": "実質収入（差引）", "現状": furusato_net, "シミュレーション": sim_net},
    ])
    compare_melted = compare_items.melt(id_vars="指標", var_name="区分", value_name="金額")
    fig_compare = px.bar(
        compare_melted, x="金額", y="指標", color="区分",
        orientation="h", barmode="group",
        color_discrete_map={"現状": "#94a3b8", "シミュレーション": "#2563eb"},
        text=compare_melted["金額"].apply(lambda x: fmt_oku(x, short=True)),
    )
    fig_compare.update_layout(
        height=300,
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
    )
    fig_compare.update_traces(
        textposition="outside", textfont_size=12,
        cliponaxis=False,
    )
    st.plotly_chart(fig_compare, use_container_width=True, config={"displayModeBar": False})

    if sim_pct == 0:
        st.markdown("""
        <div class="highlight-box">
            <strong>ふるさと納税がゼロの場合</strong><br>
            ・歳入が約10億円減少し、予算規模は大幅に縮小します<br>
            ・一方で返礼品・広告費等の運営コスト（約4.7億円）も不要になります<br>
            ・差引で約5.4億円の実質的な財源を失うことになります<br>
            ・自主財源比率（ふるさと納税除く）は変わりません。これが「町の実力」です
        </div>
        """, unsafe_allow_html=True)
    elif sim_pct < 100:
        loss = furusato_net - sim_net
        st.markdown(f"""
        <div class="highlight-box">
            <strong>ふるさと納税が{sim_pct}%に減少した場合</strong><br>
            ・実質収入が{fmt_oku(loss)}減少します<br>
            ・運営コストも比例して減りますが、寄附金の減少分を補えません<br>
            ・ふるさと納税以外の自主財源の強化が課題になります
        </div>
        """, unsafe_allow_html=True)
    elif sim_pct > 100:
        gain = sim_net - furusato_net
        st.markdown(f"""
        <div class="highlight-box">
            <strong>ふるさと納税が{sim_pct}%に増加した場合</strong><br>
            ・実質収入が{fmt_oku(gain)}増加します<br>
            ・ただしコスト率は約{safe_pct(furusato_cost_total, furusato_rev):.0f}%で一定と仮定しています。実際には広告効率の変化等で変動します<br>
            ・規模拡大に伴う人件費・事務負担の増加にも注意が必要です
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# タブ6: 特別会計
# ═══════════════════════════════════════════════════════════
with tab6:
    st.markdown('<div class="section-title">太良町の会計全体像</div>', unsafe_allow_html=True)
    st.caption("一般会計のほかに、水道・病院・国保などを別に管理する会計があります")

    # 特別会計サマリーデータ
    sa_all = special_accounts.copy()
    sa_total_current = int(sa_all["amount_current"].sum())
    sa_total_previous = int(sa_all["amount_previous"].sum())
    sa_total_diff = sa_total_current - sa_total_previous
    sa_special = sa_all[sa_all["account_name"] != "一般会計"]
    sa_special_total = int(sa_special["amount_current"].sum())
    sa_transfer_total = int(sa_special["transfer_from_general"].sum())

    _sa_diff_pct = safe_pct(sa_total_diff, sa_total_previous)
    _sa_transfer_pct = safe_pct(sa_transfer_total, sa_special_total)
    st.markdown(f"""
    <div class="highlight-box">
        <strong>特別会計のポイント</strong><br>
        ・町全体の予算は<strong>{fmt_oku(sa_total_current)}</strong>（一般会計+特別会計等）。前年度比<strong>{fmt_diff(sa_total_diff)}</strong>（{_sa_diff_pct:+.1f}%）<br>
        ・特別会計等は<strong>{fmt_oku(sa_special_total)}</strong>で、うち<strong>{fmt_oku(sa_transfer_total)}</strong>（{_sa_transfer_pct:.0f}%）が一般会計からの繰出金<br>
        ・国保・介護・後期高齢者医療の3会計で特別会計の大半を占めます
    </div>
    """, unsafe_allow_html=True)

    # サマリーカード
    sp1, sp2, sp3, sp4 = st.columns(4)
    with sp1:
        st.markdown(f'<div class="indicator-card"><div class="indicator-label">町全体の予算</div><div class="indicator-value">{fmt_oku(sa_total_current)}</div><div class="indicator-sub">前年{fmt_oku(sa_total_previous)}</div></div>', unsafe_allow_html=True)
    with sp2:
        st.markdown(f'<div class="indicator-card"><div class="indicator-label">一般会計</div><div class="indicator-value">{fmt_oku(total_exp)}</div><div class="indicator-sub">全体の{total_exp/sa_total_current*100:.1f}%</div></div>', unsafe_allow_html=True)
    with sp3:
        st.markdown(f'<div class="indicator-card"><div class="indicator-label">特別会計等</div><div class="indicator-value">{fmt_oku(sa_special_total)}</div><div class="indicator-sub">全体の{sa_special_total/sa_total_current*100:.1f}%</div></div>', unsafe_allow_html=True)
    with sp4:
        st.markdown(f'<div class="indicator-card"><div class="indicator-label">一般会計からの繰出</div><div class="indicator-value clr-pink">{fmt_oku(sa_transfer_total)}</div><div class="indicator-sub">歳出の{sa_transfer_total/total_exp*100:.1f}%</div></div>', unsafe_allow_html=True)

    # ── 各会計別予算額（横棒グラフ）──
    st.markdown('<div class="section-title">各会計別予算額</div>', unsafe_allow_html=True)
    st.caption("各会計の予算規模を比較。棒にカーソルを合わせると前年比も表示")

    sa_chart = sa_all.copy()
    sa_chart["short_name"] = sa_chart["account_name"].str.replace("特別会計", "").str.replace("事業会計", "").str.replace("会計", "")
    sa_chart = sa_chart.sort_values("amount_current", ascending=True)
    sa_chart["label"] = sa_chart["amount_current"].apply(lambda x: fmt_oku(x, short=True))
    sa_chart["change_label"] = sa_chart.apply(
        lambda r: f"{'+'if r['diff']>0 else ''}{fmt_oku(abs(int(r['diff'])), short=True)}（{'+'if r['change_rate']>0 else ''}{r['change_rate']:.1f}%）", axis=1)

    sa_colors = {
        "一般": "#3b82f6",
        "町立太良病院": "#f43f5e",
        "国民健康保険": "#f97316",
        "後期高齢者医療": "#a855f7",
        "簡易水道": "#06b6d4",
        "漁業集落排水": "#22c55e",
        "水道": "#0ea5e9",
    }

    fig_sa = go.Figure()
    for _, row in sa_chart.iterrows():
        name = row["short_name"]
        color = sa_colors.get(name, "#94a3b8")
        fig_sa.add_trace(go.Bar(
            x=[row["amount_current"]], y=[name],
            orientation="h", name=name,
            marker_color=color,
            text=[row["label"]],
            textposition="outside",
            textfont=dict(size=12),
            hovertemplate=f"{row['account_name']}<br>R8: {fmt_oku(int(row['amount_current']))}<br>R7: {fmt_oku(int(row['amount_previous']))}<br>増減: {row['change_label']}<extra></extra>",
        ))
    fig_sa.update_layout(
        height=max(250, len(sa_chart) * 45),
        margin=dict(l=0, r=70, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
        bargap=0.3,
    )
    fig_sa.update_traces(cliponaxis=False)
    st.plotly_chart(fig_sa, use_container_width=True, config={"displayModeBar": False})

    # ── 前年度比較テーブル ──
    sa_table = sa_all[["account_name", "amount_current", "amount_previous", "diff", "change_rate", "composition_ratio", "transfer_from_general", "note"]].copy()
    sa_table.columns = ["会計名", "R8年度", "R7年度", "増減額", "増減率(%)", "構成比(%)", "一般会計繰出", "増減の要因"]
    sa_table["R8年度表示"] = sa_table["R8年度"].apply(fmt_oku)
    sa_table["R7年度表示"] = sa_table["R7年度"].apply(fmt_oku)
    sa_table["増減表示"] = sa_table.apply(
        lambda r: f"{'+'if r['増減額']>0 else ''}{fmt_oku(abs(int(r['増減額'])))}", axis=1)
    sa_table["繰出表示"] = sa_table["一般会計繰出"].apply(lambda x: fmt_oku(x) if x > 0 else "-")

    # 合計行
    total_row = pd.DataFrame([{
        "会計名": "総計",
        "R8年度表示": fmt_oku(sa_total_current),
        "R7年度表示": fmt_oku(sa_total_previous),
        "増減表示": f"+{fmt_oku(sa_total_diff)}" if sa_total_diff > 0 else fmt_oku(sa_total_diff),
        "増減率(%)": round(sa_total_diff / sa_total_previous * 100, 1),
        "構成比(%)": 100.0,
        "繰出表示": fmt_oku(sa_transfer_total),
        "増減の要因": "",
    }])
    display_table = pd.concat([
        sa_table[["会計名", "R8年度表示", "R7年度表示", "増減表示", "増減率(%)", "構成比(%)", "繰出表示"]],
        total_row[["会計名", "R8年度表示", "R7年度表示", "増減表示", "増減率(%)", "構成比(%)", "繰出表示"]],
    ], ignore_index=True)
    display_table.columns = ["会計名", "R8年度", "R7年度", "増減", "増減率(%)", "構成比(%)", "一般会計繰出"]

    st.dataframe(display_table, use_container_width=True, hide_index=True, height=400)

    # ── 構成比ドーナツ ──
    st.markdown('<div class="section-title">会計別構成比</div>', unsafe_allow_html=True)
    st.caption("町全体の予算のうち、各会計が占める割合")

    dn_col1, dn_col2 = st.columns(2)
    with dn_col1:
        sa_tree = sa_all.copy()
        sa_tree["short_name"] = sa_tree["account_name"].str.replace("特別会計", "").str.replace("事業会計", "").str.replace("会計", "")
        sa_tree_colors = {n: sa_colors.get(n, "#94a3b8") for n in sa_tree["short_name"]}
        fig_sa_tree = px.treemap(
            sa_tree, path=["short_name"], values="amount_current",
            color="short_name",
            color_discrete_map=sa_tree_colors,
        )
        fig_sa_tree.update_layout(
            height=380,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        fig_sa_tree.update_traces(
            texttemplate="<b>%{label}</b><br>%{value:,.0f}千円<br>%{percentRoot:.1%}",
            hovertemplate="<b>%{label}</b><br>%{value:,.0f}千円<br>%{percentRoot:.1%}<extra></extra>",
            textfont_size=12,
        )
        st.plotly_chart(fig_sa_tree, use_container_width=True, config={"displayModeBar": False})

    with dn_col2:
        # 増減の要因
        st.markdown('<div style="font-weight:600;margin-bottom:8px">主な増減の要因</div>', unsafe_allow_html=True)
        for _, r in sa_all.iterrows():
            if r["account_name"] == "一般会計":
                continue
            diff_val = int(r["diff"])
            if diff_val == 0:
                continue
            color = "#dc2626" if diff_val > 0 else "#2563eb"
            sign = "+" if diff_val > 0 else ""
            short_name = r["account_name"].replace("特別会計", "").replace("事業会計", "").replace("会計", "")
            note = r["note"] if pd.notna(r["note"]) else ""
            st.markdown(
                f'<div style="margin-bottom:6px;padding:6px 10px;background:#f8fafc;border-radius:6px;border-left:3px solid {color}">'
                f'<strong>{short_name}</strong> '
                f'<span style="color:{color};font-weight:600">{sign}{fmt_oku(abs(diff_val))}</span><br>'
                f'<span style="font-size:0.82rem;color:#64748b">{note}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── 一般会計からの繰出金 ──
    st.markdown(f'<div class="section-title">一般会計からの{tip("繰出金")}</div>', unsafe_allow_html=True)
    st.caption("一般会計から各特別会計・企業会計へ繰り出されている金額。地域医療（太良病院）への支出が最大。")

    # 繰出金データ（予算書ベース）
    sa_transfer = sa_special[sa_special["transfer_from_general"] > 0].copy()
    sa_transfer["short_name"] = sa_transfer["account_name"].str.replace("特別会計", "").str.replace("事業会計", "").str.replace("会計", "")
    sa_transfer = sa_transfer.sort_values("transfer_from_general", ascending=True)
    sa_transfer["label"] = sa_transfer["transfer_from_general"].apply(lambda x: fmt_oku(x, short=True))
    sa_transfer["ratio"] = sa_transfer["transfer_from_general"] / sa_transfer["amount_current"] * 100

    transfer_colors = [sa_colors.get(n, "#94a3b8") for n in sa_transfer["short_name"]]

    fig_transfer = go.Figure()
    for i, (_, row) in enumerate(sa_transfer.iterrows()):
        name = row["short_name"]
        fig_transfer.add_trace(go.Bar(
            x=[row["transfer_from_general"]], y=[name],
            orientation="h", name=name,
            marker_color=sa_colors.get(name, "#94a3b8"),
            text=[row["label"]],
            textposition="outside",
            textfont=dict(size=12),
            hovertemplate=f"{row['account_name']}<br>繰出金: {fmt_oku(int(row['transfer_from_general']))}<br>会計予算の{row['ratio']:.1f}%<extra></extra>",
        ))
    fig_transfer.update_layout(
        height=max(180, len(sa_transfer) * 50),
        margin=dict(l=0, r=50, t=10, b=10),
        xaxis=dict(visible=False),
        yaxis=dict(title=""),
        showlegend=False,
    )
    fig_transfer.update_traces(cliponaxis=False)
    st.plotly_chart(fig_transfer, use_container_width=True, config={"displayModeBar": False})

    # ── 各会計の主要事業 ──
    mp_special = major_projects[major_projects["account_type"] != "一般会計"]
    if not mp_special.empty:
        st.markdown('<div class="section-title">各会計の主要事業</div>', unsafe_allow_html=True)
        st.caption("特別会計・企業会計で行われている主な事業")

        mp_by_acct = mp_special.groupby("account_type").agg(
            事業数=("id", "count"),
            合計額=("amount_current", "sum"),
        ).reset_index().sort_values("合計額", ascending=False)

        for _, sa_row in mp_by_acct.iterrows():
            acct = sa_row["account_type"]
            acct_projects = mp_special[mp_special["account_type"] == acct].sort_values("amount_current", ascending=False)

            # 対応する特別会計の情報
            sa_match = sa_all[sa_all["account_name"].str.contains(acct.replace("会計", "").replace("特別", "").replace("事業", "")[:4])]
            transfer_amt = int(sa_match["transfer_from_general"].iloc[0]) if not sa_match.empty else 0
            budget_amt = int(sa_match["amount_current"].iloc[0]) if not sa_match.empty else 0

            lines = []
            lines.append(f'<div class="highlight-box">')
            lines.append(f'<strong>{acct}</strong>')
            if budget_amt > 0:
                lines.append(f'<span style="float:right;color:#1e3a5f;font-weight:700">{fmt_oku(budget_amt)}</span>')
            lines.append('<br>')
            if transfer_amt > 0:
                lines.append(f'<span style="font-size:0.85rem;color:#ec4899">一般会計からの繰出金: {fmt_oku(transfer_amt)}（予算の{safe_pct(transfer_amt, budget_amt):.0f}%）</span><br>')
            for _, r in acct_projects.iterrows():
                is_new = "🆕 " if r.get("is_new", 0) == 1 else ""
                lines.append(f'<span style="font-size:0.9rem">・{is_new}{r["project_name"]}　{fmt_oku(int(r["amount_current"]))}</span><br>')
            lines.append('</div>')
            st.markdown(''.join(lines), unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# タブ7: 款ドリルダウン・検索
# ═══════════════════════════════════════════════════════════
with tab7:
    st.markdown(f"""
    <div class="highlight-box">
        <strong>予算を調べる</strong><br>
        ・{tip("款")}を選ぶと{tip("項")}→{tip("目")}→{tip("節")}の階層で予算の中身を掘り下げられます<br>
        ・財源構成や分析メモも自動で表示されます<br>
        ・下部のキーワード検索で全款横断の明細検索も可能です
    </div>
    """, unsafe_allow_html=True)

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

        # 歳出の場合は財源構成比を表示
        if pd.notna(kuan_sum.get("src_national")):
            st.markdown(f'<div class="section-title">{selected_kuan} の財源構成</div>', unsafe_allow_html=True)
            st.caption("この分野の予算がどこからのお金で賄われているか")
            src_vals = {
                "国・県支出金": int(kuan_sum["src_national"]) if pd.notna(kuan_sum["src_national"]) else 0,
                "地方債": int(kuan_sum["src_bond"]) if pd.notna(kuan_sum["src_bond"]) else 0,
                "その他特定財源": int(kuan_sum["src_other"]) if pd.notna(kuan_sum["src_other"]) else 0,
                "一般財源": int(kuan_sum["src_general"]) if pd.notna(kuan_sum["src_general"]) else 0,
            }
            src_pie_data = pd.DataFrame([
                {"財源": k, "金額": v} for k, v in src_vals.items() if v > 0
            ])
            if not src_pie_data.empty:
                src_pie_colors = {
                    "国・県支出金": "#2563eb",
                    "地方債": "#f97316",
                    "その他特定財源": "#22c55e",
                    "一般財源": "#94a3b8",
                }
                fig_src_pie = px.pie(
                    src_pie_data, values="金額", names="財源",
                    color="財源", color_discrete_map=src_pie_colors,
                    hole=0.5,
                )
                fig_src_pie.update_layout(
                    height=300, margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
                )
                fig_src_pie.update_traces(
                    textinfo="label+percent", textfont_size=12,
                    hovertemplate="<b>%{label}</b><br>%{percent}<br>%{value:,}千円<extra></extra>",
                )
                st.plotly_chart(fig_src_pie, use_container_width=True, config={"displayModeBar": False})

        st.markdown("")

        # 目別集計
        moku_agg = kuan_detail.groupby(["kou", "moku"]).agg(
            amount_current=("amount_current", "first"),
        ).reset_index().drop_duplicates().sort_values("amount_current", ascending=False)

        st.markdown(f'<div class="section-title">{selected_kuan} の目別内訳</div>', unsafe_allow_html=True)
        st.caption("この分野の中の細かい項目ごとの金額。上位15件を表示")

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
            margin=dict(l=0, r=50, t=10, b=10),
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
        st.caption("節（具体的な支出の種類）レベルの一覧。列の見出しで並べ替え可能")
        cols_show = ["kou", "moku", "setsu", "setsu_amount", "src_general", "description"]
        rename_map = {
            "kou": "項", "moku": "目", "setsu": "節", "setsu_amount": "金額(千円)",
            "src_general": "一般財源", "description": "説明",
        }
        display_df = kuan_detail[cols_show].rename(columns=rename_map)
        st.dataframe(display_df, use_container_width=True, height=500)

        # ── ここを聞いてみよう（自動生成チェックリスト） ──
        st.markdown(f'<div class="section-title">この款のチェックポイント</div>', unsafe_allow_html=True)
        st.caption("データから自動検出した、この款の特徴的な点です。")

        CHECK_CONTEXT = {
            ("change", "increase"): ("前年より大きく増えた分野。新事業や制度変更の可能性", "なぜ増えた？一時的か継続的か？"),
            ("change", "decrease"): ("予算減少はサービス縮小の可能性あり", "住民への影響は？代替手段は？"),
            ("source", "high_general"): ("町の持ち出しが大きい＝町の優先度が高い分野", "なぜ町独自の予算を多く充てている？"),
            ("source", "bond"): ("借金を使う事業は将来の返済負担になる", "返済期間と総額は？"),
            ("source", "national"): ("国県の補助が大きい事業は補助制度変更の影響を受けやすい", "補助率は何割？なくなったら？"),
            ("detail", "large"): ("高額な個別経費は妥当性を確認する価値あり", "金額の根拠は？入札・見積もりは？"),
        }

        check_items = []

        # 1. 款全体の増減
        kuan_diff = int(kuan_sum["diff"])
        kuan_prev = int(kuan_sum["amount_previous"])
        if kuan_prev > 0:
            kuan_change_pct = kuan_diff / kuan_prev * 100
            if abs(kuan_change_pct) >= 5:
                direction = "増加" if kuan_diff > 0 else "減少"
                _subtype = "increase" if kuan_diff > 0 else "decrease"
                check_items.append((
                    "change", _subtype,
                    f"{selected_kuan}全体が前年比<b>{kuan_change_pct:+.1f}%</b>（{fmt_diff(kuan_diff)}）{direction}しています。"
                ))

        # 2. 目レベルで大きく増減したもの
        moku_detail = kuan_detail.groupby(["kou", "moku"]).agg(
            amount_current=("amount_current", "first"),
            amount_previous=("amount_previous", "first"),
        ).reset_index().drop_duplicates()
        moku_detail["diff"] = moku_detail["amount_current"] - moku_detail["amount_previous"]
        moku_detail["diff_abs"] = moku_detail["diff"].abs()
        big_movers = moku_detail[moku_detail["diff_abs"] >= 10000].sort_values("diff_abs", ascending=False).head(3)
        for _, m in big_movers.iterrows():
            d = int(m["diff"])
            direction = "増" if d > 0 else "減"
            _subtype = "increase" if d > 0 else "decrease"
            prev = int(m["amount_previous"])
            pct = d / prev * 100 if prev > 0 else 0
            check_items.append((
                "change", _subtype,
                f"<b>{m['moku']}</b>（{m['kou']}）が{fmt_diff(d)}（{pct:+.0f}%）{direction}。"
            ))

        # 3. 財源構成に関する着眼点
        src_nat = int(kuan_sum["src_national"]) if pd.notna(kuan_sum.get("src_national")) else 0
        src_gen = int(kuan_sum["src_general"]) if pd.notna(kuan_sum.get("src_general")) else 0
        src_bond = int(kuan_sum["src_bond"]) if pd.notna(kuan_sum.get("src_bond")) else 0
        kuan_total = int(kuan_sum["amount_current"])
        if kuan_total > 0:
            gen_ratio_val = src_gen / kuan_total * 100
            if gen_ratio_val >= 80:
                check_items.append((
                    "source", "high_general",
                    f"一般財源充当率が<b>{gen_ratio_val:.0f}%</b>と高く、ほぼ町の自主財源で賄っています。"
                ))
            if src_bond > 0:
                bond_ratio = src_bond / kuan_total * 100
                check_items.append((
                    "source", "bond",
                    f"地方債を<b>{fmt_oku(src_bond)}</b>（{bond_ratio:.0f}%）充当しています。"
                ))
            if src_nat > 0 and src_nat / kuan_total * 100 >= 20:
                check_items.append((
                    "source", "national",
                    f"国・県支出金が<b>{fmt_oku(src_nat)}</b>（{safe_pct(src_nat, kuan_total):.0f}%）を占めています。"
                ))

        # 4. 大きな節（高額な個別経費）
        big_setsu = kuan_detail[
            kuan_detail["setsu_amount"].notna() & (kuan_detail["setsu_amount"] >= 50000)
        ].sort_values("setsu_amount", ascending=False).head(3)
        for _, s in big_setsu.iterrows():
            desc = s["description"] if pd.notna(s["description"]) and s["description"] else ""
            desc_short = f"（{desc[:30]}…）" if len(desc) > 30 else (f"（{desc}）" if desc else "")
            check_items.append((
                "detail", "large",
                f"<b>{s['moku']}</b>の{s['setsu']}に<b>{fmt_oku(int(s['setsu_amount']))}</b>{desc_short}。"
            ))

        # 表示
        if check_items:
            tag_labels = {"change": "増減", "source": "財源", "detail": "明細"}
            tag_classes = {"change": "tag-change", "source": "tag-source", "detail": "tag-detail"}
            items_html = ""
            for tag, subtype, text in check_items:
                tag_label = tag_labels[tag]
                tag_class = tag_classes[tag]
                ctx = CHECK_CONTEXT.get((tag, subtype))
                items_html += (
                    f'<div class="check-item">'
                    f'<span class="tag {tag_class}">{tag_label}</span>{text}'
                )
                if ctx:
                    why, question = ctx
                    items_html += (
                        f'<br><span style="font-size:0.8rem;color:#64748b">💡 {why}</span>'
                        f'<br><span style="font-size:0.8rem;color:#3b82f6">❓ 質問例：{question}</span>'
                    )
                items_html += '</div>'
            check_html = (
                '<div class="check-box">'
                '<div class="check-box-title">分析メモ</div>'
                + items_html +
                '</div>'
            )
            st.markdown(check_html, unsafe_allow_html=True)
        else:
            st.info("この款には特に大きな変動はありません。")


    # ── 明細検索 ──
    st.markdown("---")
    st.markdown('<div class="section-title">明細検索</div>', unsafe_allow_html=True)
    st.caption("全分野を横断してキーワードで検索。結果はCSV出力も可能")
    search_query = st.text_input("キーワードで検索", "", placeholder="例: 補助金、道路、学校...")

    if search_query:
        search_text = (
            detail["kuan"].fillna("") + " " +
            detail["kou"].fillna("") + " " +
            detail["moku"].fillna("") + " " +
            detail["setsu"].fillna("") + " " +
            detail["description"].fillna("")
        ).str.lower()

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
    st.download_button("CSV出力", csv, "budget_detail.csv", "text/csv", key="search_csv")



# ── フッター ──
st.markdown("---")
st.caption("太良町の予算データを町民の皆さまに分かりやすくお届けするための可視化ツールです。データは公式の予算書に基づいています。")
st.caption("正式なデータは原本（予算書）をご確認ください。 | [令和8年度予算書（町公式）](https://www.town.tara.lg.jp/chosei/_1726/_2042/_7492.html)")
st.caption("© 2026 太良町議会議員 山口一生 | Powered by Streamlit")
