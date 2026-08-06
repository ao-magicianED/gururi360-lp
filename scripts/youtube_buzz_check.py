"""あおサロンAIチャンネルの動画で急上昇（バズ）していないかを検知し、あればDiscordに通知する。

判定方法: 直近8日分の日次再生数をYouTube Analytics APIから取得し、
「直近1日の再生数」が「その前6日間の平均」の一定倍を超えていたら通知する。
状態の永続化はしない（毎回API側の時系列データだけで判定できる設計。
GitHub Actionsはリポジトリへの書き込みなしで安全に毎日回せる）。

Runs in GitHub Actions (see .github/workflows/youtube-buzz-alert.yml)。
必須env: YT_OAUTH_CLIENT_ID, YT_OAUTH_CLIENT_SECRET, YT_REFRESH_TOKEN, DISCORD_WEBHOOK_URL
"""

import os
from datetime import date, datetime, timedelta

import requests

from youtube_analytics_lib import (
    analytics_query,
    get_access_token,
    get_my_channel,
    get_recent_video_ids,
    get_videos_meta,
    to_num,
)

# 直近平均の何倍で「急上昇」とみなすか。ノイズを避けるための最低再生数の下限もあわせて設定する。
SPIKE_RATIO = 2.5
MIN_YESTERDAY_VIEWS = 20

TODAY = date.today()
# Analytics APIのデータ反映ラグを考慮し、2日前を「直近1日」として扱う
LATEST_DAY = TODAY - timedelta(days=2)
WINDOW_START = LATEST_DAY - timedelta(days=6)


def fetch_daily_views(token, video_id):
    data = analytics_query(
        token,
        ids="channel==MINE",
        startDate=WINDOW_START.isoformat(),
        endDate=LATEST_DAY.isoformat(),
        metrics="views",
        dimensions="day",
        filters=f"video=={video_id}",
        sort="day",
    )
    rows = data.get("rows") or []
    return {row[0]: to_num(row[1]) for row in rows}


def published_before_window(meta):
    """バズ判定には最低1週間分の実績が要るため、直近発売の動画は対象外にする"""
    published_at = meta["snippet"]["publishedAt"]  # 例: '2026-07-26T05:31:00Z'
    published_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
    return published_date <= WINDOW_START


def check_video(token, video_id, meta):
    if not meta or not published_before_window(meta):
        return None

    daily = fetch_daily_views(token, video_id)
    days = [WINDOW_START + timedelta(days=i) for i in range((LATEST_DAY - WINDOW_START).days + 1)]
    series = [daily.get(d.isoformat(), 0.0) for d in days]

    *history, latest_views = series
    if not history:
        return None
    if latest_views < MIN_YESTERDAY_VIEWS:
        return None

    baseline = sum(history) / len(history)
    ratio = latest_views / baseline if baseline > 0 else float("inf")
    if ratio < SPIKE_RATIO:
        return None

    return {
        "video_id": video_id,
        "title": meta["snippet"]["title"],
        "day": days[-1].isoformat(),
        "views": int(latest_views),
        "baseline": baseline,
        "ratio": ratio,
    }


def build_message(hits):
    lines = ["**🔥 あおサロンAI チャンネル 急上昇アラート**", ""]
    for h in hits:
        ratio_label = "急増" if h["ratio"] == float("inf") else f"直近平均の {h['ratio']:.1f}倍"
        lines.append(
            f"・{h['title']}\n"
            f"  {h['day']}: {h['views']:,}回再生（{ratio_label}）\n"
            f"  https://youtu.be/{h['video_id']}"
        )
    return "\n".join(lines)


def main():
    token = get_access_token()
    channel = get_my_channel(token)
    uploads_playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
    video_ids = get_recent_video_ids(token, uploads_playlist, max_results=15)
    videos_meta = get_videos_meta(token, video_ids)

    hits = [h for h in (check_video(token, vid, videos_meta.get(vid)) for vid in video_ids) if h]

    if not hits:
        print("急上昇なし（Discordへの投稿はスキップ）")
        return

    hits.sort(key=lambda h: h["ratio"], reverse=True)
    message = build_message(hits)

    resp = requests.post(os.environ["DISCORD_WEBHOOK_URL"], json={"content": message}, timeout=15)
    resp.raise_for_status()
    print("Posted to Discord:\n", message)


if __name__ == "__main__":
    main()
