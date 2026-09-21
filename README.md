# Fragments

文字を追い続けたいが、悪口や怒りは浴びたくない人のための、古い言葉だけが流れるタイムラインです。

## ローカル確認

```sh
python3 extract_quotes.py
npm run build
python3 -m http.server 4173 --directory dist/client
```

## 公開方針

GitHub はソース管理とデプロイの起点に使い、本番は独自ドメインを設定した Cloudflare Pages から配信します。GitHub Pages は広告なしの短期プレビュー以外には使いません。

Cloudflare Pages の設定値と、ドメイン・広告導入の順序は [DEPLOYMENT.md](DEPLOYMENT.md) を参照してください。コンテンツの選定基準は [CONTENT_STRATEGY.md](CONTENT_STRATEGY.md) にまとめています。
