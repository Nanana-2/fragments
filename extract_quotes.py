# File: extract_quotes.py
import re
import json
import glob
import os
import hashlib

DEFAULT_MAX_QUOTES = 1000

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

    # 詩は改行を意味として残し、SNSで読める長さまで行を束ねる。
    if len(lines) > 1 and sum(map(len, lines)) / len(lines) < 28:
        pieces = lines
        separator = "\n"
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

        # 一文だけで上限を超える場合は、読点などを優先して再分割する。
        while len(piece) > max_len:
            cut = max(
                piece.rfind(mark, min_len, max_len + 1)
                for mark in ("、", "，", "；", "：", "—")
            )
            cut = cut + 1 if cut >= min_len else max_len
            chunks.append(piece[:cut].strip())
            piece = piece[cut:].strip()
        current = piece

    if min_len <= len(current) <= max_len:
        chunks.append(current)
    elif current and chunks and len(chunks[-1]) + len(separator) + len(current) <= max_len:
        chunks[-1] = f"{chunks[-1]}{separator}{current}"

    return chunks


def chunk_text(text: str, author: str, work: str, year: str = "", min_len: int = 35, max_len: int = 140) -> list:
    """
    本文を段落単位に分割し、Xのタイムラインとして読みやすい長さにフィルタリングする
    """
    raw_blocks = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    results = []
    seen_texts = set()

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
                seen_texts.add(clean_p)
                # 一意なIDの生成（テキストと作者のハッシュ）
                uid = hashlib.md5(f"{author}_{work}_{clean_p}".encode('utf-8')).hexdigest()[:8]
                results.append({
                    "id": f"{author[:2]}_{uid}",
                    "author": author,
                    "work": work,
                    "year": year,
                    "text": clean_p
                })

    return results

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

    # 作品ごとの偏りを避けるため、各作品から順番に1件ずつ採用する。
    all_quotes = []
    for index in range(max((len(quotes) for quotes in quotes_by_work), default=0)):
        for quotes in quotes_by_work:
            if index < len(quotes):
                all_quotes.append(quotes[index])
                if len(all_quotes) >= max_quotes:
                    break
        if len(all_quotes) >= max_quotes:
            break

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_quotes, f, ensure_ascii=False, indent=2)

    print(f"\n総計 {len(all_quotes)} 件の断片を '{output_file}' に書き出しました。")

if __name__ == "__main__":
    process_directory()
