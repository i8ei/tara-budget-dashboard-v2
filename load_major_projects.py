#!/usr/bin/env python3
"""主要事業一覧（Vault md）をパースしてmajor_projectsテーブルに投入"""
import re
import sqlite3
import os

MD_PATH = "/Users/issei/Documents/Obsidian Vault/予算/令和8年度_主要事業一覧.md"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "budget_r8.db")


def parse_amount(s):
    """金額文字列→整数（千円）。空文字やNoneは0"""
    if not s or not s.strip():
        return 0
    s = s.strip().replace(",", "").replace("，", "")
    try:
        return int(s)
    except ValueError:
        return 0


def parse_md_table(lines):
    """Markdownテーブル行をパースして辞書リストを返す"""
    rows = []
    headers = None
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if headers is None:
            headers = cells
            continue
        # セパレータ行（---）をスキップ
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def main():
    with open(MD_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # セクション別に分割
    sections = re.split(r'^## ', content, flags=re.MULTILINE)

    all_projects = []
    for section in sections:
        if not section.strip():
            continue
        section_title = section.split("\n")[0].strip()

        # 会計区分を判定
        if "一般会計" in section_title:
            account_type = "一般会計"
        elif "後期高齢者" in section_title:
            account_type = "後期高齢者医療特別会計"
        elif "国民健康保険" in section_title:
            account_type = "国民健康保険特別会計"
        elif "漁業集落排水" in section_title:
            account_type = "漁業集落排水事業会計"
        elif "簡易水道" in section_title:
            account_type = "簡易水道事業会計"
        elif "水道事業" in section_title:
            account_type = "水道事業会計"
        elif "太良病院" in section_title:
            account_type = "町立太良病院事業会計"
        else:
            continue

        lines = section.split("\n")
        rows = parse_md_table(lines)

        for row in rows:
            seq_raw = row.get("連番", "")
            is_new = 1 if "新" in seq_raw else 0
            seq = parse_amount(re.sub(r'[^\d]', '', seq_raw))

            project = {
                "seq": seq,
                "page": parse_amount(row.get("頁", "")),
                "department": row.get("担当課", "").replace("〃", ""),
                "budget_category": row.get("予算科目", "").replace("〃", ""),
                "project_name": row.get("事業名", ""),
                "is_new": is_new,
                "amount_current": parse_amount(row.get("本年度", "")),
                "amount_previous": parse_amount(row.get("前年度", "")),
                "description": row.get("説明", ""),
                "account_type": account_type,
            }

            # 一般会計は財源内訳あり
            if account_type == "一般会計":
                project["src_national"] = parse_amount(
                    re.sub(r'（.*?）', '', row.get("国県支出金", ""))
                )
                project["src_bond"] = parse_amount(
                    re.sub(r'（.*?）', '', row.get("地方債", ""))
                )
                project["src_other"] = parse_amount(
                    re.sub(r'（.*?）', '', row.get("その他", ""))
                )
                project["src_general"] = parse_amount(
                    re.sub(r'（.*?）', '', row.get("一般財源", ""))
                )
            else:
                project["src_national"] = 0
                project["src_bond"] = 0
                project["src_other"] = 0
                project["src_general"] = 0

            all_projects.append(project)

    # 「〃」の解決（前の行の値を引き継ぐ）
    prev_dept = ""
    prev_cat = ""
    for p in all_projects:
        if p["department"]:
            prev_dept = p["department"]
        else:
            p["department"] = prev_dept
        if p["budget_category"]:
            prev_cat = p["budget_category"]
        else:
            p["budget_category"] = prev_cat

    # DB投入
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM major_projects")

    for p in all_projects:
        cur.execute("""
            INSERT INTO major_projects
            (seq, page, department, budget_category, project_name, is_new,
             amount_current, amount_previous, src_national, src_bond,
             src_other, src_general, description, account_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            p["seq"], p["page"], p["department"], p["budget_category"],
            p["project_name"], p["is_new"], p["amount_current"],
            p["amount_previous"], p["src_national"], p["src_bond"],
            p["src_other"], p["src_general"], p["description"],
            p["account_type"],
        ))

    conn.commit()
    count = cur.execute("SELECT COUNT(*) FROM major_projects").fetchone()[0]
    new_count = cur.execute("SELECT COUNT(*) FROM major_projects WHERE is_new=1").fetchone()[0]
    ippan = cur.execute("SELECT COUNT(*) FROM major_projects WHERE account_type='一般会計'").fetchone()[0]
    conn.close()

    print(f"投入完了: {count}件（うち新規{new_count}件、一般会計{ippan}件）")

    # 担当課別サマリー
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT department, COUNT(*) as cnt, SUM(amount_current) as total,
               SUM(CASE WHEN is_new=1 THEN 1 ELSE 0 END) as new_cnt
        FROM major_projects WHERE account_type='一般会計'
        GROUP BY department ORDER BY total DESC
    """).fetchall()
    conn.close()
    print("\n担当課別（一般会計）:")
    for r in rows:
        print(f"  {r[0]}: {r[1]}件（新規{r[3]}件）, {r[2]:,}千円")


if __name__ == "__main__":
    main()
