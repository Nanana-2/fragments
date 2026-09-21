#!/usr/bin/env python3
"""Wikidataで作者本人を照合し、CommonsでPDと確認できた肖像だけを取得する。"""

import json
import mimetypes
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


ROOT = Path(__file__).resolve().parent.parent
QUOTES_PATH = ROOT / "quotes.json"
INDEX_PATH = ROOT / "index.html"
AVATAR_DIR = ROOT / "avatars"
MANIFEST_PATH = ROOT / "avatar_manifest.json"
SOURCES_PATH = ROOT / "avatar_sources.json"
USER_AGENT = "FragmentsLiteratureFeed/1.0 (public-domain portrait verifier)"
PD_LICENSES = ("public domain", "cc0", "pdm")


def api_json(base: str, params: dict[str, str]) -> dict:
    url = f"{base}?{urllib.parse.urlencode(params)}"
    for attempt in range(4):
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("API request failed")


def existing_authors() -> set[str]:
    source = INDEX_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*'([^']+)':\s*'\./avatars/", source, re.MULTILINE))


def chunks(items: list, size: int) -> list[list]:
    return [items[index:index + size] for index in range(0, len(items), size)]


def matching_entities(authors: list[str]) -> dict[str, Tuple[str, dict]]:
    author_qids = {}
    for batch in chunks(authors, 40):
        result = api_json("https://ja.wikipedia.org/w/api.php", {
            "action": "query",
            "titles": "|".join(batch),
            "prop": "pageprops",
            "ppprop": "wikibase_item",
            "redirects": "1",
            "format": "json",
        })
        normalized = {item["to"]: item["from"] for item in result.get("query", {}).get("normalized", [])}
        redirects = {item["to"]: item["from"] for item in result.get("query", {}).get("redirects", [])}
        for page in result.get("query", {}).get("pages", {}).values():
            title = page.get("title", "")
            original = redirects.get(title, normalized.get(title, title))
            if original in authors and page.get("pageprops", {}).get("wikibase_item"):
                author_qids[original] = page["pageprops"]["wikibase_item"]

    entities = {}
    qids = list(dict.fromkeys(author_qids.values()))
    for batch in chunks(qids, 40):
        result = api_json("https://www.wikidata.org/w/api.php", {
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "claims",
            "format": "json",
        })
        entities.update(result.get("entities", {}))

    matches = {}
    for author, qid in author_qids.items():
        entity = entities.get(qid, {})
        instance_ids = {
            claim.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
            for claim in entity.get("claims", {}).get("P31", [])
        }
        if "Q5" in instance_ids:
            matches[author] = (qid, entity)
    return matches


def commons_images(filenames: list[str]) -> dict[str, dict]:
    results = {}
    for batch in chunks(filenames, 25):
        data = api_json("https://commons.wikimedia.org/w/api.php", {
            "action": "query",
            "titles": "|".join(f"File:{filename}" for filename in batch),
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": "320",
            "format": "json",
        })
        for page in data.get("query", {}).get("pages", {}).values():
            info = (page.get("imageinfo") or [None])[0]
            if not info:
                continue
            metadata = info.get("extmetadata", {})
            license_name = metadata.get("LicenseShortName", {}).get("value", "")
            usage_terms = metadata.get("UsageTerms", {}).get("value", "")
            if not any(marker in f"{license_name} {usage_terms}".lower() for marker in PD_LICENSES):
                continue
            filename = page.get("title", "").removeprefix("File:")
            results[filename.replace("_", " ")] = {
                "download_url": info.get("thumburl") or info["url"],
                "mime": info.get("thumbmime") or info.get("mime", "image/jpeg"),
                "license": license_name or usage_terms,
                "description_url": info.get("descriptionurl"),
            }
    return results


def download(url: str, path: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        path.write_bytes(response.read())


def main() -> None:
    authors = sorted({item["author"] for item in json.loads(QUOTES_PATH.read_text(encoding="utf-8"))})
    skip = existing_authors()
    pending = [author for author in authors if author not in skip]
    matches = matching_entities(pending)
    portraits = {}
    for author, (_, entity) in matches.items():
        claims = entity.get("claims", {}).get("P18", [])
        if claims:
            portraits[author] = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
    images = commons_images(list(dict.fromkeys(filename for filename in portraits.values() if filename)))
    manifest = {}
    sources = []
    AVATAR_DIR.mkdir(exist_ok=True)

    for author in authors:
        if author in skip:
            continue
        try:
            match = matches.get(author)
            if not match:
                print(f"文字アイコン（本人を一意に照合できず）: {author}")
                continue
            qid, entity = match
            filename = portraits.get(author)
            if not filename:
                print(f"文字アイコン（肖像なし）: {author}")
                continue
            info = images.get(filename.replace("_", " "))
            if not info:
                print(f"文字アイコン（PD確認不可）: {author}")
                continue
            extension = mimetypes.guess_extension(info["mime"]) or Path(urllib.parse.urlparse(info["download_url"]).path).suffix
            if extension == ".jpe":
                extension = ".jpg"
            local_name = f"wikidata-{qid.lower()}{extension or '.jpg'}"
            download(info["download_url"], AVATAR_DIR / local_name)
            manifest[author] = f"./avatars/{local_name}"
            sources.append({
                "author": author,
                "wikidata_id": qid,
                "commons_file": filename,
                "source_url": info["description_url"],
                "license": info["license"],
                "local_path": manifest[author],
            })
            print(f"取得: {author} / {qid} / {info['license']}", flush=True)
        except Exception as error:
            print(f"文字アイコン（取得失敗）: {author}: {error}")

    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SOURCES_PATH.write_text(json.dumps(sources, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n新規肖像 {len(manifest)}名 / 全作者 {len(authors)}名 / 既存肖像 {len(skip & set(authors))}名")


if __name__ == "__main__":
    main()
