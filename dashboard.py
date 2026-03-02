#!/usr/bin/env python3
"""太良町 予算ダッシュボード — ビュー切り替えエントリポイント"""
import streamlit as st

st.set_page_config(
    page_title="太良町 予算ダッシュボード",
    page_icon="🏛️",
    layout="wide",
)

# CSS注入
from common import inject_css
inject_css()

# ── ビュー切り替え ──
view = st.sidebar.radio("ビュー", [
    "📋 令和8年度 詳細",
    "📊 3年比較（R6〜R8）",
    "🏥 病院事業会計",
])

if view.startswith("📋"):
    import view_single
    view_single.render()
elif view.startswith("📊"):
    import view_compare
    view_compare.render()
else:
    import view_hospital
    view_hospital.render()

# ── フッター ──
st.markdown("---")
st.caption("太良町の予算データを町民の皆さまに分かりやすくお届けするための可視化ツールです。データは公式の予算書に基づいています。")
st.caption("正式なデータは原本（予算書）をご確認ください。 | [令和8年度予算書（町公式）](https://www.town.tara.lg.jp/chosei/_1726/_2042/_7492.html)")
st.caption("© 2026 太良町議会議員 山口一生 | Powered by Streamlit")
