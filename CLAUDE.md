# CLAUDE.md（gururi360-lp）

## 概要
「ぐるり360」（あお×久保田宙/くぼちゅーの相互送客協業ブランド）の外販用LP。民泊・レンタルスペースのオーナー向けに、360度内見ツアー制作サービスを訴求する単一HTMLの静的サイト。ビルドツールなし、`public/index.html` 1ファイルで完結（画像・favicon等はすべてdata URIで自己完結）。

## コマンド
```bash
# ローカル確認
python -m http.server 8000 --directory public
# → http://localhost:8000

# デプロイ（Cloudflare Pages）
CLOUDFLARE_ACCOUNT_ID=d1baf436df81893d1f8478a3cda0c082 npx wrangler@4 pages deploy public --project-name=gururi360 --branch=main --commit-message="update"
```
- 本番URL: https://gururi360.pages.dev
- commit-messageはASCIIのみ推奨（日本語でUTF-8エラーが出た前例があるプロジェクトあり）

## 規約・注意
- `public/index.html` は完全自己完結（外部CDN・外部フォント・fetch禁止）。唯一の外部リンクはヒルトップ逗子デモURLとLINE公式（`https://lin.ee/W7oKNWT`）。
- 統計データ（効果データセクション）は出典検証済みのもの以外を追加しない。使用禁止の統計リスト・設計書は `hilltop-zushi-360-deploy` プロジェクトの scratchpad（`lp-spec.md`）にある。
- ブランド名「ぐるり360」・ロゴ・favicon（「ぐ」1文字、UDデジタル教科書体Bold）はメモリ（hilltop-zushi-360-deployプロジェクトの `partnership_kubochu_360.md`）で管理。変更時はそちらも更新する。
