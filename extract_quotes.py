# File: extract_quotes.py
import glob
import hashlib
import json
import os
import re
from collections import Counter
from typing import Optional


DEFAULT_MAX_QUOTES = 800
MIN_LEN = 12
MAX_LEN = 100
MAX_PER_AUTHOR = 60

TONE_RATIOS = {
    "white": 0.25,
    "black": 0.25,
    "blue": 0.15,
    "gold": 0.35,
}

# 長編小説は意図的に対象外。短詩、箴言、身辺随筆・日記だけを明示的に許可する。
SOURCE_PROFILES = {
    "一握の砂": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "悲しき玩具": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "尾崎放哉選句集": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "草木塔": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "山羊の歌": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "青猫": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "純情小曲集": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "和歌でない歌": {"source_type": "poetry", "tone": "gold", "mode": "poetry_lines"},
    "春と修羅": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "みだれ髪": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "桐の花": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "秋の瞳": {"source_type": "poetry", "tone": "gold", "mode": "poetry"},
    "侏儒の言葉": {"source_type": "aphorism", "tone": "black", "mode": "prose"},
    "自省録（独自訳）": {"source_type": "aphorism", "tone": "blue", "mode": "prose"},
    "ツァラトゥストラ（独自訳）": {"source_type": "aphorism", "tone": "black", "mode": "prose"},
    "提要（独自訳）": {"source_type": "aphorism", "tone": "blue", "mode": "prose"},
    "罪・苦痛・希望・及び真実の道についての考察": {"source_type": "aphorism", "tone": "black", "mode": "prose_blocks"},
    "科学者とあたま": {"source_type": "essay", "tone": "blue", "mode": "prose"},
    "行乞記": {"source_type": "diary", "tone": "white", "mode": "prose"},
    "一日中の楽しき時刻": {"source_type": "diary", "tone": "white", "mode": "prose"},
    "病牀六尺": {"source_type": "diary", "tone": "white", "mode": "prose"},
    "料理の秘訣": {"source_type": "essay", "tone": "white", "mode": "prose"},
    "小学生のとき与へられた教訓": {"source_type": "essay", "tone": "white", "mode": "prose"},
    "回想録": {"source_type": "essay", "tone": "white", "mode": "prose"},
}

CONTEXTUAL_OPENINGS = re.compile(
    r"^(彼女|彼|その|この|あの|これ|それ|それから|この男|しかし|だが|だから|ところで|そして|"
    r"けれども|けれど|そこで|すると|そうして|こうして|さて|やがて|また一方|"
    r"従って|したがって|しかるに|なお|もっとも|尤も|実は|一方|要するに|今考えると)"
)

CONVERSATION_ENDINGS = re.compile(
    r"(?:と(?:言|云|答|呟|つぶや)[^。]{0,8}(?:た|った|ました|ます)。?|[」』])$"
)

INCOMPLETE_ENDINGS = re.compile(r"(?:、|，|て|ので|けれど|けれども)$")
SPECIAL_CHARACTERS = re.compile(r"[�\uFFFD※]|［|］|〔|〕|／＼")
SECTION_HEADING = re.compile(r"^[［【〈].+[］】〉]$")
DEPENDENT_PHRASES = re.compile(
    r"(次のよう|次のやう|前述|上述|以上の|後述|その人|その時|そのため|このこと|この点|"
    r"この場合|これを読|それについて|さう云ふ|そういう|と言うので|といふので)"
)
POETRY_META = re.compile(
    r"(霊前|本書|修証義|序に代|序文|青空文庫|底本|初出|編者|著者|選句|句集|改版|昭和|明治|大正|西暦|年作|月作)"
)


def clean_aozora_text(raw_text: str) -> str:
    """青空文庫のヘッダー、フッター、ルビ、注記を除去する。"""
    text = raw_text
    if "-------" in text:
        text = text.split("-------")[-1]
    if "底本：" in text:
        text = text.split("底本：")[0]
    text = re.sub(r"［＃[^］]+］", "", text)
    text = re.sub(r"《[^》]+》", "", text)
    text = text.replace("｜", "")
    text = re.sub(r"\r\n|\r", "\n", text)
    return text.strip()


def strip_outer_quote(text: str) -> str:
    """断片全体を包む一組だけの鉤括弧を外す。"""
    pairs = {"「": "」", "『": "』"}
    opening = text[:1]
    closing = pairs.get(opening)
    if not closing or not text.endswith(closing):
        return text

    depth = 0
    for index, char in enumerate(text):
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0 and index != len(text) - 1:
                return text
    return text[1:-1].strip() if depth == 0 else text


def normalize_candidate(text: str, work: str) -> str:
    lines = [re.sub(r"[ \t　]+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line and not SECTION_HEADING.fullmatch(line)]
    text = "\n".join(lines).strip()
    text = re.sub(r"^[×△☆○]+[　 ]*", "", text)
    if work == "法句経":
        text = re.sub(r"^[〇一二三四五六七八九零]{2,4}[　 ]+", "", text)
    return strip_outer_quote(text)


def hiragana_ratio(text: str) -> float:
    hiragana = len(re.findall(r"[ぁ-ん]", text))
    readable_japanese = len(re.findall(r"[ぁ-ん一-龯々]", text))
    return hiragana / readable_japanese if readable_japanese else 0.0


def standalone_score(text: str, source_type: str, mode: str) -> Optional[int]:
    """0.5秒で読み始められ、単体で閉じている断片だけを採用する。"""
    compact_len = len(text.replace("\n", ""))
    lines = text.splitlines()
    if not MIN_LEN <= compact_len <= MAX_LEN or not 1 <= len(lines) <= 3:
        return None
    if CONTEXTUAL_OPENINGS.search(text) or SPECIAL_CHARACTERS.search(text):
        return None
    if mode.startswith("prose") and DEPENDENT_PHRASES.search(text):
        return None
    if mode.startswith("prose") and re.search(r"(?:（[一二三四五六七八九十]+月[^）]*）|^[（(][月火水木金土日][）)])", text):
        return None
    if mode.startswith("poetry") and POETRY_META.search(text):
        return None
    if mode.startswith("poetry") and re.match(r"^[0-9〇一二三四五六七八九十]+[―—-]", text):
        return None
    if mode.startswith("poetry") and re.match(r"^(トンネルへ|すべてこれらの命題は)", text):
        return None
    if mode.startswith("poetry") and len(re.findall(r"[。！？]", text)) > 2:
        return None
    if mode.startswith("poetry") and len(text.replace("\n", "")) > 70 and text.endswith("。"):
        return None
    if re.fullmatch(r"[\s\d一二三四五六七八九十百千（\）()・]+", text):
        return None
    if not re.search(r"[ぁ-んァ-ヶ一-龯々]", text):
        return None
    if text.count("「") != text.count("」") or text.count("『") != text.count("』"):
        return None
    if text.count("（") != text.count("）"):
        return None
    if CONVERSATION_ENDINGS.search(text) or INCOMPLETE_ENDINGS.search(text):
        return None
    if re.search(r"[、，：；（「『—―]$", text):
        return None
    if mode.startswith("prose") and not re.search(r"[。！？…）]$", text):
        return None
    if mode.startswith("prose") and len(re.findall(r"[。！？]", text)) > 3:
        return None

    minimum_ratio = 0.12 if mode.startswith("poetry") else 0.18
    if hiragana_ratio(text) < minimum_ratio:
        return None

    score = {"poetry": 155, "aphorism": 150, "diary": 135, "essay": 125}[source_type]
    if 18 <= compact_len <= 72:
        score += 16
    elif compact_len <= 88:
        score += 8
    if re.search(r"(私|わたし|われ|自分|ひとり|一人|こころ|心|生き|死|好き|悲|淋|寂|働|金|酒|眠|夢)", text):
        score += 18
    if re.search(r"(朝|夜|雨|雪|風|花|月|山|海|空|猫|犬|食|飲|笑|泣|病|旅|家|友)", text):
        score += 8
    if re.search(r"(これ|それ|あれ|ここに|そこに|ような|わけで|のである|という|といふ)", text):
        score -= 18
    if mode.startswith("poetry") and len(lines) <= 3:
        score += 12
    return score


def poetry_candidates(text: str) -> list[str]:
    """短歌の三行組と自由律俳句の一行を、そのまま一投稿として扱う。"""
    candidates = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        # 原句の直後に添えられた括弧内の現代表記は重複投稿にしない。
        lines = [line for line in lines if not (line.startswith("（") and line.endswith("）"))]
        if not lines or len(lines) > 3:
            continue
        candidates.append("\n".join(lines))
    return candidates


def poetry_line_candidates(text: str) -> list[str]:
    """一行一首で組まれた歌集を、改行単位で扱う。"""
    return [line.strip() for line in text.splitlines() if line.strip()]


def prose_candidates(text: str) -> list[str]:
    """短い元段落、または長い段落中でも単独で完結した一文だけを候補にする。"""
    candidates = []
    for block in re.split(r"\n\s*\n", text):
        block = "".join(line.strip() for line in block.splitlines() if line.strip())
        if not block:
            continue
        if len(block) <= MAX_LEN:
            candidates.append(block)
            continue
        candidates.extend(
            piece.strip()
            for piece in re.findall(r".*?(?:[。！？]+[」』）]?|$)", block)
            if piece.strip() and len(re.findall(r"[。！？]", piece)) == 1
        )
    return candidates


def prose_block_candidates(text: str) -> list[str]:
    """元から短い段落だけを扱い、箴言を文単位に分断しない。"""
    return [
        "".join(line.strip() for line in block.splitlines() if line.strip())
        for block in re.split(r"\n\s*\n", text)
        if block.strip()
    ]


def extract_work(text: str, author: str, work: str, year: str, profile: dict) -> list[dict]:
    if profile["mode"] == "poetry":
        raw_candidates = poetry_candidates(text)
    elif profile["mode"] == "poetry_lines":
        raw_candidates = poetry_line_candidates(text)
    elif profile["mode"] == "prose_blocks":
        raw_candidates = prose_block_candidates(text)
    else:
        raw_candidates = prose_candidates(text)
    results = []
    seen_texts = set()

    for raw_candidate in raw_candidates:
        candidate = normalize_candidate(raw_candidate, work)
        if not candidate or candidate in seen_texts:
            continue
        quality = standalone_score(candidate, profile["source_type"], profile["mode"])
        if quality is None:
            continue
        seen_texts.add(candidate)
        uid = hashlib.md5(f"{author}_{work}_{candidate}".encode("utf-8")).hexdigest()[:8]
        results.append({
            "id": f"{author[:2]}_{uid}",
            "author": author,
            "work": work,
            "year": year,
            "text": candidate,
            "source_type": profile["source_type"],
            "tone": profile["tone"],
            "_quality": quality,
        })

    return sorted(results, key=lambda item: item["_quality"], reverse=True)


def read_text(filepath: str) -> Optional[str]:
    for encoding in ("utf-8", "cp932", "shift_jis", "euc-jp"):
        try:
            with open(filepath, "r", encoding=encoding) as source:
                return source.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def select_balanced(quotes_by_work: list[list[dict]], max_quotes: int) -> list[dict]:
    selected = []
    selected_ids = set()
    author_counts = Counter()
    targets = {tone: round(max_quotes * ratio) for tone, ratio in TONE_RATIOS.items()}
    targets["white"] += max_quotes - sum(targets.values())

    def add(item: dict, enforce_cap: bool = True) -> bool:
        if item["id"] in selected_ids:
            return False
        if enforce_cap and author_counts[item["author"]] >= MAX_PER_AUTHOR:
            return False
        selected.append(item)
        selected_ids.add(item["id"])
        author_counts[item["author"]] += 1
        return True

    for tone, target in targets.items():
        pools = [[item for item in work if item["tone"] == tone] for work in quotes_by_work]
        pools = [pool for pool in pools if pool]
        tone_count = 0
        for index in range(max((len(pool) for pool in pools), default=0)):
            for pool in pools:
                if index < len(pool) and add(pool[index]):
                    tone_count += 1
                if tone_count >= target:
                    break
            if tone_count >= target:
                break

    remaining = sorted(
        (item for work in quotes_by_work for item in work if item["id"] not in selected_ids),
        key=lambda item: item["_quality"],
        reverse=True,
    )
    for item in remaining:
        if len(selected) >= max_quotes:
            break
        add(item)
    return selected


def process_directory(input_dir: str = "./texts", output_file: str = "quotes.json", max_quotes: int = DEFAULT_MAX_QUOTES):
    if not os.path.exists(input_dir):
        os.makedirs(input_dir, exist_ok=True)
        return

    quotes_by_work = []
    for filepath in sorted(glob.glob(os.path.join(input_dir, "*.txt"))):
        filename = os.path.splitext(os.path.basename(filepath))[0]
        parts = filename.split("_")
        author = parts[0] if parts else "不明"
        work = parts[1] if len(parts) > 1 else "無題"
        year = parts[2] if len(parts) > 2 else ""
        profile = SOURCE_PROFILES.get(work)
        if profile is None:
            print(f"対象外: {author}『{work}』")
            continue

        raw = read_text(filepath)
        if raw is None:
            print(f"スキップ（文字コード判別不能）: {filepath}")
            continue
        quotes = extract_work(clean_aozora_text(raw), author, work, year, profile)
        quotes_by_work.append(quotes)
        print(f"抽出完了: {author}『{work}』 -> {len(quotes)} 件")

    selected = select_balanced(quotes_by_work, max_quotes)
    for item in selected:
        item.pop("_quality", None)

    with open(output_file, "w", encoding="utf-8") as destination:
        json.dump(selected, destination, ensure_ascii=False, indent=2)

    authors = len({item["author"] for item in selected})
    print(f"\n総計 {len(selected)} 件・{authors}名の断片を '{output_file}' に書き出しました。")


if __name__ == "__main__":
    process_directory()
