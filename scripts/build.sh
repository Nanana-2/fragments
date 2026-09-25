#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dist_dir="$project_dir/dist"

rm -rf "$dist_dir"
mkdir -p "$dist_dir/client" "$dist_dir/server"

for file in index.html avatar_manifest.json manifest.json icon-192.png icon-512.png ogp.png; do
  cp "$project_dir/$file" "$dist_dir/client/$file"
done

python3 "$project_dir/scripts/build_quote_shards.py" \
  "$project_dir/quotes.json" \
  "$dist_dir/client/quote-shards" \
  "$dist_dir/client/quote-manifest.json"

cp -R "$project_dir/avatars" "$dist_dir/client/avatars"

cp "$project_dir/worker.js" "$dist_dir/server/index.js"
