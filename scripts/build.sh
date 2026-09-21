#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dist_dir="$project_dir/dist"

rm -rf "$dist_dir"
mkdir -p "$dist_dir/client" "$dist_dir/server"

for file in index.html quotes.json manifest.json icon-192.png icon-512.png ogp-v2.png; do
  cp "$project_dir/$file" "$dist_dir/client/$file"
done

cp "$project_dir/worker.js" "$dist_dir/server/index.js"
