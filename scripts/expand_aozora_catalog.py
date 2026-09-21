#!/usr/bin/env python3
"""短詩・随筆・日記の追加作者を、青空文庫の権利情報から再現可能に選定する。"""

import csv
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "content_catalog.json"
INDEX_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"

NEW_AUTHORS = [
    "宮本百合子", "岸田国士", "中谷宇吉郎", "佐藤垢石", "大町桂月", "堀辰雄",
    "泉鏡花", "片山広子", "薄田泣菫", "森川義信", "岡本綺堂", "長谷川時雨",
    "折口信夫", "夢野久作", "伊藤野枝", "北村透谷", "原民喜", "富永太郎",
    "若山牧水", "吉川英治", "正宗白鳥", "山之口貘", "森鴎外", "野上豊一郎",
    "横光利一", "北条民雄", "高浜虚子", "野口雨情", "宮城道雄", "三好十郎",
    "伊丹万作", "海野十三", "久保田万太郎", "小酒井不木", "辻潤", "正岡容",
    "菊池寛", "会津八一", "野村胡堂", "淡島寒月", "尾形亀之助", "辰野隆",
    "谷崎潤一郎", "内田魯庵", "平林初之輔", "岩野泡鳴", "木下杢太郎",
    "杉田久女", "百田宗治", "吉井勇", "岩本素白", "河井酔茗", "三木清",
    "九鬼周造", "阿部次郎", "国木田独歩", "上田敏", "小山清", "河上肇",
    "二葉亭四迷",
]

EXCLUDE_TITLE = re.compile(
    r"(戦争|戦時|戦線|戦話|敗戦|進軍|政治|選挙|国家|国民|革命|階級|共産|ソヴェト|"
    r"労働|露西亜|騒擾|原爆|軍隊|軍人|軍国|闘争|事件|犯罪|殺人|自殺|解剖|"
    r"論争|批評|選評|研究|解説|書評|作品評|文学論|作家論|を読む|作者の言葉|"
    r"追悼|弔辞|瘋癲老人日記|序に代|序文|初版の序|跋|あとがき|はしがき|全集|刊行|創作評|月評)"
)
PREFER_TITLE = re.compile(
    r"(日記|日誌|手紙|書翰|消息|随筆|断片|小品|雑記|覚え書|独語|ひとりごと|"
    r"酒|食|猫|犬|生活|一日|朝|夜|雨|雪|月|花|海|山|川|風|春|夏|秋|冬|旅|夢|"
    r"心|自己|人生|自然|美|孤独|思い出|回想)"
)


def profile(row: dict[str, str]) -> dict[str, str]:
    ndc = row.get("分類番号", "")
    title = row["作品名"]
    if "911" in ndc:
        return {"source_type": "poetry", "tone": "gold", "mode": "poetry"}
    if "915" in ndc or "916" in ndc:
        return {"source_type": "diary", "tone": "white", "mode": "prose"}
    if re.search(r"(死|孤独|恐怖|憂|苦|毒|怒|悪|貧)", title):
        tone = "black"
    elif re.search(r"(哲学|人生|自己|心|自然|美|芸術|思想|生)", title):
        tone = "blue"
    elif re.search(r"(春|夏|秋|冬|雨|雪|月|花|海|山|川|風|夜|朝|夢)", title):
        tone = "gold"
    else:
        tone = "white"
    return {"source_type": "essay", "tone": tone, "mode": "prose"}


def row_score(row: dict[str, str]) -> int:
    notation = row.get("文字遣い種別", "")
    notation_score = {"新字新仮名": 32, "新字旧仮名": 20, "旧字新仮名": 14, "旧字旧仮名": 4}.get(notation, 0)
    ndc = row.get("分類番号", "")
    genre_score = 24 if ("915" in ndc or "916" in ndc) else 18 if "911" in ndc else 12
    title = row["作品名"]
    return notation_score + genre_score + (24 if PREFER_TITLE.search(title) else 0) + (8 if len(title) <= 12 else 0)


def main() -> None:
    with urllib.request.urlopen(INDEX_URL, timeout=60) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
    rows = list(csv.DictReader(io.StringIO(archive.read(csv_name).decode("utf-8-sig"))))

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    retained = [item for item in catalog if item["author"] not in NEW_AUTHORS]
    additions = []
    for author in NEW_AUTHORS:
        candidates = [
            row for row in rows
            if row.get("姓", "") + row.get("名", "") == author
            and row.get("役割フラグ") == "著者"
            and row.get("作品著作権フラグ") == "なし"
            and row.get("人物著作権フラグ") == "なし"
            and row.get("テキストファイルURL")
            and re.search(r"(?:911|914|915|916)", row.get("分類番号", ""))
            and not EXCLUDE_TITLE.search(row.get("作品名", ""))
        ]
        best_by_title = {}
        for row in candidates:
            title = row["作品名"]
            if title not in best_by_title or row_score(row) > row_score(best_by_title[title]):
                best_by_title[title] = row
        ranked = sorted(best_by_title.values(), key=lambda row: (-row_score(row), row["作品名"]))
        chosen = ranked[:5]
        if not chosen:
            raise RuntimeError(f"候補作品がありません: {author}")
        for row in chosen:
            additions.append({"author": author, "work": row["作品名"], **profile(row)})
            print(f"追加: {author}『{row['作品名']}』 ({row['分類番号']})")

    CATALOG_PATH.write_text(
        json.dumps(retained + additions, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n追加 {len(additions)}作品 / 合計 {len(retained) + len(additions)}作品")


if __name__ == "__main__":
    main()
