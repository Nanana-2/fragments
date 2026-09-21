# File: extract_quotes.py
import re
import json
import glob
import os
import hashlib
from typing import Optional

DEFAULT_MAX_QUOTES = 600

TONE_RATIOS = {
    "white": 0.35,
    "black": 0.25,
    "blue": 0.25,
    "gold": 0.15,
}

MIN_QUALITY = {
    "fiction": 124,
    "classic": 140,
    "essay": 122,
    "diary": 110,
    "poetry": 128,
    "aphorism": 145,
}

SOURCE_PROFILES = {
    "山羊の歌": {"source_type": "poetry", "tone": "gold"},
    "青猫": {"source_type": "poetry", "tone": "gold"},
    "侏儒の言葉": {"source_type": "aphorism", "tone": "black"},
    "続堕落論": {"source_type": "essay", "tone": "black"},
    "現代訳論語": {"source_type": "classic", "tone": "blue"},
    "法句経": {"source_type": "classic", "tone": "blue"},
    "一日中の楽しき時刻": {"source_type": "diary", "tone": "white"},
}

CONTEXTUAL_OPENINGS = re.compile(
    r'^(そして|しかし|けれども|けれど|だが|それから|そこで|すると|ところが|'
    r'のみならず|また一方|つまり|こうして|そうして|さて|やがて|いきなり|'
    r'もちろん|実は|もっとも|その|この|あの|それは|これは|彼は|彼女は)'
)

ATTRIBUTION_ONLY_ENDINGS = re.compile(
    r'(言|云|答|尋|たず|訊|話|返事|質問|叫|怒鳴|説明)\w{0,8}(ました|ます|った|いう|云う)。?$'
)

def clean_aozora_text(raw_text: str) -> str:
    """
    青空文庫テキスト特有のルビ記法・注記タグ・ヘッダー/フッターを除去する
    """
    text = raw_text

    # ヘッダー情報の切断（------ で囲まれた書誌情報以降を本文とする）
    if "-------" in text:
        parts = text.split("-------")
        text = parts[-1]

    # 底本情報以降のフッターを切断
    if "底本：" in text:
        text = text.split("底本：")[0]

    # 青空文庫タグの除去
    text = re.sub(r'［＃[^］]+］', '', text)       # ［＃見出し］［＃改ページ］等
    text = re.sub(r'《[^》]+》', '', text)       # 《ルビ》
    text = re.sub(r'｜', '', text)                 # ルビ開始位置記号
    text = re.sub(r'\r\n|\r', '\n', text)          # 改行コード統一

    return text.strip()

def _split_long_unit(unit: str, min_len: int, max_len: int) -> list[str]:
    """長い段落を文の切れ目で、短い詩行を数行ずつまとめて分割する。"""
    lines = [line.strip() for line in unit.split('\n') if line.strip()]

    # 詩は一行でも欠けると意味が壊れやすいため、長い連は切り刻まず見送る。
    if len(lines) > 1 and sum(map(len, lines)) / len(lines) < 28:
        return []
    else:
        prose = "".join(lines)
        pieces = [
            piece.strip()
            for piece in re.findall(r'.*?(?:[。！？]+[」』）】]?|$)', prose)
            if piece.strip()
        ]
        separator = ""

    chunks = []
    current = ""
    for piece in pieces:
        candidate = f"{current}{separator if current else ''}{piece}"
        if len(candidate) <= max_len:
            current = candidate
            continue

        if len(current) >= min_len:
            chunks.append(current)
            current = ""

        # 一文の途中を機械的に切った断片は採用しない。
        current = piece if len(piece) <= max_len else ""

    if min_len <= len(current) <= max_len:
        chunks.append(current)
    elif current and chunks and len(chunks[-1]) + len(separator) + len(current) <= max_len:
        chunks[-1] = f"{chunks[-1]}{separator}{current}"

    return chunks


def standalone_score(text: str, source_type: str) -> Optional[int]:
    """単体で読める断片だけを残し、編集上の優先度を返す。"""
    is_poetry = "\n" in text
    if text.startswith("○") or CONTEXTUAL_OPENINGS.search(text):
        return None
    if re.fullmatch(r'[\s\d一二三四五六七八九十百千（\）()]+', text):
        return None
    if text.count("「") != text.count("」") or text.count("『") != text.count("』"):
        return None
    if text.count("（") != text.count("）"):
        return None
    if not is_poetry and not re.search(r'[。！？…」』）]$', text):
        return None
    if re.search(r'[、，：；（「『—―]$', text) or ATTRIBUTION_ONLY_ENDINGS.search(text):
        return None

    score = 100
    score += {"aphorism": 35, "classic": 30, "essay": 16, "diary": 12, "poetry": 24}.get(source_type, 0)
    score += min(len(re.findall(r'[。！？]', text)), 3) * 4
    if text.startswith(("「", "『")) and text.endswith(("」", "』")):
        score += 12
    if re.search(r'(私は|自分は|人間は|人生|幸福|自由|孤独|言葉|真理|生き|死|愛|心)', text):
        score += 8
    if 55 <= len(text) <= 120:
        score += 6
    return score


def chunk_text(text: str, author: str, work: str, year: str = "", min_len: int = 35, max_len: int = 140) -> list:
    """
    本文を段落単位に分割し、Xのタイムラインとして読みやすい長さにフィルタリングする
    """
    raw_blocks = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    results = []
    seen_texts = set()
    profile = SOURCE_PROFILES.get(work, {"source_type": "fiction", "tone": "white"})

    for block in raw_blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if not lines:
            continue

        # 青空文庫の小説は一段落一改行、詩は短い行の連なりであることが多い。
        if len(lines) > 4 and sum(map(len, lines)) / len(lines) >= 28:
            units = lines
        else:
            units = ["\n".join(lines)]

        for unit in units:
            candidates = [unit] if min_len <= len(unit) <= max_len else _split_long_unit(unit, min_len, max_len)
            for clean_p in candidates:
                # 日本語を含まない断片と重複を除外する。
                if clean_p in seen_texts or not re.search(r'[ぁ-んァ-ヶ一-龯々]', clean_p):
                    continue
                if not min_len <= len(clean_p) <= max_len:
                    continue
                if work == "法句経" and not re.match(r'^[〇一二三四五六七八九零]{2,4}[　 ]', clean_p):
                    continue
                if work == "現代訳論語" and not ("「" in clean_p and "」" in clean_p):
                    continue
                quality = standalone_score(clean_p, profile["source_type"])
                if quality is None or quality < MIN_QUALITY[profile["source_type"]]:
                    continue
                seen_texts.add(clean_p)
                # 一意なIDの生成（テキストと作者のハッシュ）
                uid = hashlib.md5(f"{author}_{work}_{clean_p}".encode('utf-8')).hexdigest()[:8]
                results.append({
                    "id": f"{author[:2]}_{uid}",
                    "author": author,
                    "work": work,
                    "year": year,
                    "text": clean_p,
                    "source_type": profile["source_type"],
                    "tone": profile["tone"],
                    "_quality": quality
                })

    return sorted(results, key=lambda item: item["_quality"], reverse=True)

def process_directory(input_dir: str = "./texts", output_file: str = "quotes.json", max_quotes: int = DEFAULT_MAX_QUOTES):
    """
    input_dir 内の全 txt ファイルを処理して output_file に出力する。
    ファイル名フォーマット想定: 「作者_作品名_年代.txt」（例: 太宰治_人間失格_1948年.txt）
    """
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)
        print(f"ディレクトリ '{input_dir}' を作成しました。青空文庫の .txt ファイルを配置してください。")
        return

    txt_files = sorted(glob.glob(os.path.join(input_dir, "*.txt")))
    if not txt_files:
        print(f"'{input_dir}' に .txt ファイルが見つかりません。")
        return

    quotes_by_work = []

    for filepath in txt_files:
        filename = os.path.splitext(os.path.basename(filepath))[0]
        parts = filename.split('_')
        
        author = parts[0] if len(parts) > 0 else "不明"
        work = parts[1] if len(parts) > 1 else "無題"
        year = parts[2] if len(parts) > 2 else ""

        # エンコーディングの自動判別（青空文庫は Shift_JIS または UTF-8）
        content = None
        for enc in ['utf-8', 'cp932', 'shift_jis', 'euc-jp']:
            try:
                with open(filepath, 'r', encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        if content is None:
            print(f"スキップ（エンコーディング判別不能）: {filepath}")
            continue

        cleaned = clean_aozora_text(content)
        quotes = chunk_text(cleaned, author, work, year)
        quotes_by_work.append(quotes)
        print(f"抽出完了: {author}『{work}』 -> {len(quotes)} 件")

    # 「日常→毒→超越→詩」の落差を作りつつ、各作品が一作だけを占有しないよう選ぶ。
    all_quotes = []
    selected_ids = set()
    targets = {tone: round(max_quotes * ratio) for tone, ratio in TONE_RATIOS.items()}
    targets["white"] += max_quotes - sum(targets.values())

    for tone, target in targets.items():
        work_pools = [[q for q in quotes if q["tone"] == tone] for quotes in quotes_by_work]
        work_pools = [pool for pool in work_pools if pool]
        for index in range(max((len(pool) for pool in work_pools), default=0)):
            for pool in work_pools:
                if index >= len(pool):
                    continue
                quote = pool[index]
                if quote["id"] in selected_ids:
                    continue
                all_quotes.append(quote)
                selected_ids.add(quote["id"])
                if sum(q["tone"] == tone for q in all_quotes) >= target:
                    break
            if sum(q["tone"] == tone for q in all_quotes) >= target:
                break

    # 小規模ソースが目標数に届かない場合は、品質順で不足分を補う。
    remaining = sorted(
        (q for quotes in quotes_by_work for q in quotes if q["id"] not in selected_ids),
        key=lambda item: item["_quality"],
        reverse=True,
    )
    all_quotes.extend(remaining[:max(0, max_quotes - len(all_quotes))])

    for quote in all_quotes:
        quote.pop("_quality", None)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)

    print(f"\n総計 {len(all_quotes)} 件の断片を '{output_file}' に書き出しました。")

if __name__ == "__main__":
    process_directory()
