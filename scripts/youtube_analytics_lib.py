"""YouTube Data API v3 + YouTube Analytics API v2 の共通ヘルパー。

長期間有効なrefresh_token（internal-youtube-uploader/scripts/authorize.mjs で取得）から
短命なaccess_tokenを都度発行する。GitHub Actions等の無人実行を前提にしており、
ここでは一切ユーザー操作（ブラウザログイン）を行わない。

必須env: YT_OAUTH_CLIENT_ID, YT_OAUTH_CLIENT_SECRET, YT_REFRESH_TOKEN
"""

import os

import requests

TOKEN_URL = "https://oauth2.googleapis.com/token"
DATA_API = "https://www.googleapis.com/youtube/v3"
ANALYTICS_API = "https://youtubeanalytics.googleapis.com/v2/reports"


def get_access_token():
    res = requests.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["YT_OAUTH_CLIENT_ID"],
            "client_secret": os.environ["YT_OAUTH_CLIENT_SECRET"],
            "refresh_token": os.environ["YT_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    res.raise_for_status()
    token = res.json().get("access_token")
    if not token:
        raise RuntimeError(f"アクセストークン取得失敗: {res.json()}")
    return token


def data_api_get(token, path, **params):
    res = requests.get(
        f"{DATA_API}/{path}",
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    res.raise_for_status()
    return res.json()


def analytics_query(token, **params):
    res = requests.get(
        ANALYTICS_API,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    res.raise_for_status()
    return res.json()


def get_my_channel(token):
    """認証したGoogleアカウント自身のチャンネル情報（id・統計・アップロード再生リストID）を返す"""
    data = data_api_get(token, "channels", part="id,snippet,statistics,contentDetails", mine="true")
    items = data.get("items", [])
    if not items:
        raise RuntimeError("チャンネルが見つかりません（mine=trueで0件）。トークンのスコープ・アカウントを確認してください")
    return items[0]


def get_recent_video_ids(token, uploads_playlist_id, max_results=15):
    """アップロード済み動画IDを新しい順で返す"""
    data = data_api_get(
        token,
        "playlistItems",
        part="contentDetails",
        playlistId=uploads_playlist_id,
        maxResults=max_results,
    )
    return [item["contentDetails"]["videoId"] for item in data.get("items", [])]


def get_videos_meta(token, video_ids):
    """複数動画のタイトル・統計をまとめて取得（50件まで一括可）。{videoId: item} の辞書で返す"""
    if not video_ids:
        return {}
    data = data_api_get(token, "videos", part="snippet,statistics", id=",".join(video_ids))
    return {item["id"]: item for item in data.get("items", [])}


TRAFFIC_SOURCE_LABELS = {
    "YT_SEARCH": "YouTube検索",
    "SUBSCRIBER": "登録者のフィード",
    "SUGGESTED_VIDEO": "関連動画（おすすめ）",
    "RELATED_VIDEO": "関連動画",
    "EXT_URL": "外部サイト・アプリ",
    "NOTIFICATION": "通知",
    "PLAYLIST": "再生リスト",
    "YT_CHANNEL": "チャンネルページ",
    "YT_OTHER_PAGE": "YouTube内その他ページ",
    "SHORTS": "Shortsフィード",
    "SHORTS_ORIGINAL": "Shorts（元動画）",
    "NO_LINK_OTHER": "その他（直接・不明）",
    "PLAYBACK_LOCATION": "その他",
    "END_SCREEN": "エンドスクリーン",
    "NO_LINK_EMBEDDED": "埋め込みプレーヤー",
    "ADVERTISING": "広告",
    "CAMPAIGN_CARD": "キャンペーンカード",
}


def traffic_label(code):
    return TRAFFIC_SOURCE_LABELS.get(code, code)


def to_num(value):
    """Analytics APIの値は数値のことが多いが、念のため文字列も許容して数値化する"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
