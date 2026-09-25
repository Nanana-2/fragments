#!/usr/bin/env python3
"""quotes.jsonを初回表示の軽い、均質な配信シャードへ分割する。"""

import json
import random
import sys
from pathlib import Path


SHARD_SIZE = 500
SHUFFLE_SEED = 20260925


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: build_quote_shards.py INPUT OUTPUT_DIR MANIFEST")

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    manifest_path = Path(sys.argv[3])
    quotes = json.loads(input_path.read_text(encoding="utf-8"))

    # 元データはtoneごとの選定順なので、各シャードに作者と文体が混ざるよう固定seedで散らす。
    random.Random(SHUFFLE_SEED).shuffle(quotes)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    for index, start in enumerate(range(0, len(quotes), SHARD_SIZE)):
        filename = f"quotes-{index:02d}.json"
        shard = quotes[start:start + SHARD_SIZE]
        (output_dir / filename).write_text(
            json.dumps(shard, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        files.append(f"quote-shards/{filename}")

    manifest_path.write_text(
        json.dumps({"total": len(quotes), "shard_size": SHARD_SIZE, "files": files}, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"{len(quotes)}件を{len(files)}シャードへ分割しました。")


if __name__ == "__main__":
    main()
