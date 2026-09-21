# 公開・ドメイン・広告導入手順

## 推奨構成

```text
GitHub repository
  └─ pushを検知
      └─ Cloudflare Pages（本番配信）
          └─ 独自ドメイン
              └─ Web広告 / 将来のPWA
```

GitHub Pages のURLを本番URLにはしない。GitHubはコードの保管、自動デプロイ、変更履歴に使う。これによりGitHubのユーザー名を来訪者向けURLに出さず、ホスティング先を変更してもドメインを維持できる。

## 1. GitHub

1. 空のリポジトリ `fragments` を作る（READMEやライセンスは追加しない）。
2. 公開前のコンテンツや運用情報を含むため、最初は private を推奨する。
3. ローカルリポジトリに remote を追加して `main` を push する。

`.openai/hosting.json` は現在の一時公開先を示すローカル設定なので、GitHubには含めない。

## 2. Cloudflare Pages

Cloudflare dashboard で Workers & Pages からGitHubリポジトリを接続し、次の値を設定する。

- Production branch: `main`
- Build command: `npm run build`
- Build output directory: `dist/client`
- Environment variables: なし

pushごとにプレビューと本番がビルドされる。広告を入れるまではCloudflareの一時URLで動作確認してよいが、一般公開の告知は独自ドメイン設定後に行う。

## 3. 独自ドメイン

短く、個人名やGitHubユーザー名を含まない名称を登録する。Cloudflare Pagesを使う場合はCloudflare Registrarで取得するとDNS設定が最も単純になる。

ドメインを接続したら、`index.html` の次の値を絶対URLに置き換える。

- `og:image`
- `twitter:image`
- `og:url`（追加）
- `twitter:url`（追加）
- `link rel="canonical"`（追加）

## 4. 広告を入れる前の条件

1. 独自ドメインで安定公開する。
2. プライバシーポリシー、問い合わせ先、運営者情報の掲載範囲を決める。
3. AdSense等の審査用コードを`head`に設置する。
4. 発行されたpublisher IDでルート直下の`ads.txt`を作る。
5. 地域に応じた同意管理を実装する。
6. 「広告」と明示した専用カードを15〜25件に1回以下で試験する。

広告を引用カードに似せない。初期段階では全画面、追従、スクロールを妨げる広告を使わず、読了率と離脱率を見て頻度を調整する。

## 5. アプリ化

まずPWAとしてフィードと推薦を検証する。ネイティブアプリ化するときは、Web広告コードを流用せず、各ストア向け広告SDK・同意画面・`app-ads.txt`を別設定として扱う。
