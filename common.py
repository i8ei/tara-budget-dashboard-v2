#!/usr/bin/env python3
"""太良町 予算ダッシュボード — 共通定数・CSS・ユーティリティ"""
import os
import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════
# 共通定数
# ══════════════════════════════════════

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

SETSU_TO_NATURE = {}
for _cat, _setsu_list in NATURE_MAP.items():
    for _s in _setsu_list:
        SETSU_TO_NATURE[_s] = _cat

NATURE_COLORS = {
    "人件費": "#2563eb", "扶助費": "#f97316", "公債費": "#f43f5e",
    "物件費": "#22c55e", "補助費等": "#a855f7", "投資的経費": "#06b6d4",
    "積立金・貸付金": "#eab308", "繰出金": "#ec4899", "その他": "#94a3b8",
}

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

KUAN_COLORS = [
    "#2563eb", "#f97316", "#22c55e", "#a855f7", "#06b6d4",
    "#f43f5e", "#eab308", "#ec4899", "#14b8a6", "#6366f1",
    "#84cc16", "#d97706", "#8b5cf6", "#94a3b8",
]

COLOR_INCREASE = "#22c55e"
COLOR_DECREASE = "#f43f5e"

# ── v2 固有定数 ──
SRC_COLORS = {
    "src_national": "#2563eb",
    "src_bond": "#f97316",
    "src_other": "#22c55e",
    "src_general": "#94a3b8",
}

POPULATION = 7_669
FURUSATO_COST_ITEMS = {
    "返礼品（謝礼）": 300_000,
    "インターネット広告": 112_802,
    "事業支援業務委託": 44_550,
    "ワンストップ特例受付": 8_069,
    "広告謝礼": 500,
}
FURUSATO_FUND_SIM = 1_000_000

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

# ── v3 固有定数 ──
DB_PATHS = {
    "R6 (2024)": os.path.join(BASE_DIR, "budget_r6.db"),
    "R7 (2025)": os.path.join(BASE_DIR, "budget_r7.db"),
    "R8 (2026)": os.path.join(BASE_DIR, "budget_r8.db"),
}
YEARS = list(DB_PATHS.keys())
YEAR_SHORT = {"R6 (2024)": "R6", "R7 (2025)": "R7", "R8 (2026)": "R8"}
YEAR_COLORS = {"R6 (2024)": "#3b82f6", "R7 (2025)": "#22c55e", "R8 (2026)": "#f43f5e"}


# ══════════════════════════════════════
# ユーティリティ関数
# ══════════════════════════════════════

def safe_pct(part, total):
    return part / total * 100 if total else 0.0

def fmt_oku(val, short=False):
    oku = val / 100000
    unit_oku = "億" if short else "億円"
    unit_man = "万" if short else "万円"
    if oku >= 1:
        return f"{oku:,.1f}{unit_oku}"
    man = val / 10
    return f"{man:,.0f}{unit_man}"

def fmt_diff(val, short=False):
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
    colloquial = KUAN_COLLOQUIAL.get(kuan_name)
    return f"{kuan_name}（{colloquial}）" if colloquial else kuan_name

def classify_revenue(kuan_name):
    if kuan_name in INDEPENDENT_REVENUE:
        return "自主財源"
    elif kuan_name in DEPENDENT_REVENUE:
        return "依存財源"
    return "その他"

def tip(term):
    desc = GLOSSARY.get(term, "")
    return f'<span class="term-tip" data-tip="{desc}">{term}</span>' if desc else term

def diff_pct_str(new, old):
    if old == 0:
        return "新規" if new > 0 else "-"
    pct = (new - old) / old * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{pct:.1f}%"

def diff_color(new, old):
    if old == 0:
        return "#2563eb"
    return COLOR_INCREASE if new >= old else COLOR_DECREASE


# ══════════════════════════════════════
# CSS 注入
# ══════════════════════════════════════

def inject_css():
    st.markdown("""
<style>
    .block-container { padding-top: 1rem; max-width: 1100px; }
    .hero-number { font-size: 3.2rem; font-weight: 800; color: #1e3a5f; line-height: 1.1; }
    .hero-label { font-size: 1rem; color: #64748b; margin-bottom: 4px; }
    .hero-sub { font-size: 1rem; font-weight: 500; }
    .hero-sub.plus { color: #22c55e; }
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
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        font-size: 1rem;
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        cursor: pointer;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: #e2e8f0;
        border-color: #94a3b8;
    }
    .stTabs [aria-selected="true"] {
        background: #2563eb !important;
        color: #fff !important;
        border-color: #2563eb !important;
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
        .stTabs [data-baseweb="tab"] { padding: 8px 10px; font-size: 0.85rem; }
        .stTabs [data-baseweb="tab-list"] { gap: 2px; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            width: 100% !important; flex: 0 0 100% !important; min-width: 100% !important;
        }
        [data-testid="stDataFrame"] { overflow-x: auto; -webkit-overflow-scrolling: touch; }
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
        .stTabs [data-baseweb="tab"] { padding: 6px 8px; font-size: 0.78rem; }
    }
</style>
""", unsafe_allow_html=True)
