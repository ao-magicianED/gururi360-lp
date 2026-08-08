/**
 * 旧URL（gururi360.pages.dev）から新ドメイン（gururi360.aosalonai.com）への301転送。
 *
 * なぜWorkerが必要か:
 *   Cloudflare Pages の `_redirects` はパスしか見られず、ホスト名で分岐できない。
 *   同じPagesプロジェクトが pages.dev と独自ドメインの両方で配信されるため、
 *   「pages.dev で来たときだけ転送する」にはこのファイルが必要。
 *
 * なぜ301（恒久的）か:
 *   公開済みのYouTube宣伝動画のフレームに旧URL（gururi360.pages.dev）が焼き込まれており、
 *   動画を作り直さない方針にしたため、旧URLは今後も踏まれ続ける。
 *   canonical と合わせて検索評価も新ドメインへ寄せる。
 *
 * 注意:
 *   - デプロイごとのプレビューURL（例 4ce38cfd.gururi360.pages.dev）は転送しない。
 *     転送するとデプロイ内容の検証ができなくなるため、production の別名だけを対象にする。
 *   - 何かあってもサイトが落ちないよう、例外は握りつぶして通常配信にフォールバックする。
 *     （env.ASSETS.fetch が静的ファイルの配信本体）
 */

const OLD_HOST = "gururi360.pages.dev";
const NEW_HOST = "gururi360.aosalonai.com";

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url);
      if (url.hostname === OLD_HOST) {
        url.hostname = NEW_HOST;
        // パス・クエリ・ハッシュは維持したまま移す
        return Response.redirect(url.toString(), 301);
      }
    } catch (err) {
      // URL解析やリダイレクト生成で失敗しても、静的配信は続ける
    }
    return env.ASSETS.fetch(request);
  },
};
