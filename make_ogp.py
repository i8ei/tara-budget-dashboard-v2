#!/usr/bin/env python3
"""Facebook投稿用のOGP画像を生成"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = "#0f172a"
ACCENT = "#2563eb"
WHITE = "#ffffff"
GRAY = "#94a3b8"
GREEN = "#22c55e"

img = Image.new("RGB", (W, H), BG)
draw = ImageDraw.Draw(img)

# フォント
font_bold_lg = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 52)
font_bold_md = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 36)
font_bold_sm = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 24)
font_reg = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 22)
font_num = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 72)
font_num_sm = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 28)

# 上部アクセント帯
draw.rectangle([(0, 0), (W, 6)], fill=ACCENT)

# タイトル
draw.text((60, 40), "太良町", fill=GRAY, font=font_bold_sm)
draw.text((60, 75), "令和８年度 予算ダッシュボード", fill=WHITE, font=font_bold_lg)

# 区切り線
draw.rectangle([(60, 148), (200, 152)], fill=ACCENT)

# 3つの数字カード
card_y = 185
cards = [
    {"label": "歳出総額", "value": "89.5", "unit": "億円", "x": 60},
    {"label": "町民1人あたり", "value": "117", "unit": "万円", "x": 440},
    {"label": "主要事業", "value": "44", "unit": "事業", "x": 820},
]

for c in cards:
    x = c["x"]
    # カード背景
    draw.rounded_rectangle(
        [(x, card_y), (x + 310, card_y + 170)],
        radius=16,
        fill="#1e293b",
        outline="#334155",
        width=1,
    )
    # ラベル
    draw.text((x + 24, card_y + 20), c["label"], fill=GRAY, font=font_reg)
    # 数値
    draw.text((x + 24, card_y + 55), c["value"], fill=WHITE, font=font_num)
    # 単位
    bbox = draw.textbbox((x + 24, card_y + 55), c["value"], font=font_num)
    draw.text((bbox[2] + 4, card_y + 90), c["unit"], fill=GRAY, font=font_num_sm)

# 下部の特徴リスト
features_y = 400
features = [
    "📊  分野ごとの予算をグラフで一覧",
    "🔍  キーワードで予算の明細を検索",
    "💡  専門用語にはやさしい説明つき",
]
for i, f in enumerate(features):
    draw.text((80, features_y + i * 42), f, fill="#cbd5e1", font=font_bold_sm)

# フッター
draw.rectangle([(0, H - 50), (W, H)], fill="#1e293b")
draw.text((60, H - 40), "太良町議会議員  山口一生", fill=GRAY, font=font_reg)
draw.text((W - 300, H - 40), "スマホ・PCで閲覧できます", fill=ACCENT, font=font_reg)

out_path = "/Users/issei/Downloads/太良町_令和8年度予算/dashboard-v2/ogp_facebook.png"
img.save(out_path, "PNG")
print(f"Saved: {out_path}")
