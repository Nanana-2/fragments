#!/usr/bin/env python3
"""公式作品一覧から、content_catalog.json で指定した青空文庫テキストを取得する。"""

import csv
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "content_catalog.json"
TEXT_DIR = ROOT / "texts"
INDEX_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"


def publication_year(row: dict[str, str]) -> str:
    first_publication = re.findall(r"(?:18|19|20)\d{2}", row.get("初出", ""))
    if first_publication:
        return f"{min(map(int, first_publication))}年"

    death_years = re.findall(r"(?:18|19|20)\d{2}", row.get("没年月日", ""))
    death_year = int(death_years[0]) if death_years else None
    edition_fields = (row.get("底本の親本初版発行年1", ""), row.get("底本初版発行年1", ""))
    edition_years = [int(year) for field in edition_fields for year in re.findall(r"(?:18|19|20)\d{2}", field)]
    plausible_years = [year for year in edition_years if death_year is None or year <= death_year]
    return f"{min(plausible_years)}年" if plausible_years else "年不詳"


def preference(row: dict[str, str]) -> tuple[int, int]:
    notation = row.get("文字遣い種別", "")
    notation_rank = {"新字新仮名": 0, "新字旧仮名": 1, "旧字新仮名": 2, "旧字旧仮名": 3}.get(notation, 4)
    ruby_rank = 1 if "_txt_" in row.get("テキストファイルURL", "") else 0
    return notation_rank, ruby_rank


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    managed_manifest = ROOT / "aozora_sources.json"
    if managed_manifest.exists():
        for old_item in json.loads(managed_manifest.read_text(encoding="utf-8")):
            old_path = TEXT_DIR / old_item["filename"]
            if old_path.is_file():
                old_path.unlink()
    with urllib.request.urlopen(INDEX_URL, timeout=60) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    csv_name = next(name for name in archive.namelist() if name.endswith(".csv"))
    rows = list(csv.DictReader(io.StringIO(archive.read(csv_name).decode("utf-8-sig"))))

    TEXT_DIR.mkdir(exist_ok=True)
    downloaded = []
    for item in catalog:
        matches = [
            row for row in rows
            if row.get("姓", "") + row.get("名", "") == item["author"]
            and row.get("作品名") == item["work"]
            and row.get("役割フラグ") == "著者"
            and row.get("作品著作権フラグ") == "なし"
            and row.get("人物著作権フラグ") == "なし"
            and row.get("テキストファイルURL")
        ]
        if not matches:
            raise RuntimeError(f"権利切れテキストが見つかりません: {item['author']}『{item['work']}』")
        row = sorted(matches, key=preference)[0]

        with urllib.request.urlopen(row["テキストファイルURL"], timeout=60) as response:
            work_archive = zipfile.ZipFile(io.BytesIO(response.read()))
        text_name = next(name for name in work_archive.namelist() if name.lower().endswith(".txt"))
        filename = f"{item['author']}_{item['work']}_{publication_year(row)}.txt"
        destination = TEXT_DIR / filename
        destination.write_bytes(work_archive.read(text_name))
        downloaded.append({
            "author": item["author"],
            "work": item["work"],
            "card_url": row["図書カードURL"],
            "text_url": row["テキストファイルURL"],
            "filename": filename,
        })
        print(f"取得: {item['author']}『{item['work']}』 -> {filename}")

    managed_manifest.write_text(
        json.dumps(downloaded, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"\n{len(downloaded)}作品を取得しました。")


if __name__ == "__main__":
    main()
