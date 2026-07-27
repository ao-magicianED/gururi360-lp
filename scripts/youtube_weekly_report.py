"""あおサロンAIチャンネルの直近7日間のYouTube成績をDiscordに投稿する。

Runs in GitHub Actions (see .github/workflows/youtube-weekly-report.yml)。
必須env: YT_OAUTH_CLIENT_ID, YT_OAUTH_CLIENT_SECRET, YT_REFRESH_TOKEN, DISCORD_WEBHOOK_URL
"""

import os
from datetime import date, timedelta

import requests

from youtube_analytics_lib import (
    analytics_query,
    get_access_token,
    get_my_channel,
    get_videos_meta,
    to_num,
    traffic_label,
)

TODAY = date.today()
# YouTube Analyticsのデータは反映まで1〜2日のラグがあるため、直近2日を除いた期間を「直近7日」として扱う
END = TODAY - timedelta(days=2)
START = END - timedelta(days=6)
PREV_END = START - timedelta(days=1)
PREV_START = PREV_END - timedelta(days=6)

METRICS = "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost,likes,comments,shares"
METRIC_KEYS = ["views", "minutes", "avgDuration", "subsGained", "subsLost", "likes", "comments", "shares"]


def fetch_totals(token, start, end):
    data = analytics_query(
        token,
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics=METRICS,
    )
    rows = data.get("rows") or []
    if not rows:
        return dict.fromkeys(METRIC_KEYS, 0.0)
    return dict(zip(METRIC_KEYS, (to_num(v) for v in rows[0])))


def fetch_top_videos(token, start, end, limit=5):
    data = analytics_query(
        token,
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views",
        dimensions="video",
        sort="-views",
        maxResults=limit,
    )
    return [(row[0], int(to_num(row[1]))) for row in (data.get("rows") or [])]


def fetch_top_traffic(token, start, end, limit=5):
    data = analytics_query(
        token,
        ids="channel==MINE",
        startDate=start.isoformat(),
        endDate=end.isoformat(),
        metrics="views",
        dimensions="insightTrafficSourceType",
        sort="-views",
        maxResults=limit,
    )
    return [(row[0], int(to_num(row[1]))) for row in (data.get("rows") or [])]


def pct_change(now, prev):
    if prev == 0:
        return "—" if now == 0 else "新規"
    diff = (now - prev) / prev * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.0f}%"


def format_hours(minutes):
    return f"{minutes / 60:.1f}時間"


def format_min_sec(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    return f"{m}分{s}秒"


def build_message(channel, totals, prev_totals, top_videos, videos_meta, top_traffic):
    views = int(totals["views"])
    prev_views = int(prev_totals["views"])

    lines = [
        "**📊 あおサロンAI チャンネル 週次レポート**",
        f"（{START.isoformat()} 〜 {END.isoformat()}）",
        "",
        f"再生回数: **{views:,}** （前週比 {pct_change(views, prev_views)}）",
        f"総再生時間: **{format_hours(totals['minutes'])}**",
        f"平均視聴時間: **{format_min_sec(totals['avgDuration'])}**",
        f"登録者増減: **+{int(totals['subsGained'])} / -{int(totals['subsLost'])}**",
        f"高評価: {int(totals['likes'])} ／ コメント: {int(totals['comments'])} ／ シェア: {int(totals['shares'])}",
        "",
        "**再生数 TOP5（今週）**",
    ]
    if not top_videos:
        lines.append("・データなし")
    else:
        for video_id, video_views in top_videos:
            meta = videos_meta.get(video_id)
            title = meta["snippet"]["title"] if meta else video_id
            lines.append(f"・{title} — {video_views:,}回\n  https://youtu.be/{video_id}")

    lines.append("")
    lines.append("**流入元 TOP5**")
    if not top_traffic:
        lines.append("・データなし")
    else:
        for source, source_views in top_traffic:
            lines.append(f"・{traffic_label(source)}: {source_views:,}回")

    lines.append("")
    stats = channel["statistics"]
    lines.append(
        f"チャンネル累計: 登録者 {int(stats['subscriberCount']):,}人 ／ 総再生 {int(stats['viewCount']):,}回"
    )

    return "\n".join(lines)


def main():
    token = get_access_token()
    channel = get_my_channel(token)

    totals = fetch_totals(token, START, END)
    prev_totals = fetch_totals(token, PREV_START, PREV_END)
    top_videos = fetch_top_videos(token, START, END)
    top_traffic = fetch_top_traffic(token, START, END)
    videos_meta = get_videos_meta(token, [video_id for video_id, _ in top_videos])

    message = build_message(channel, totals, prev_totals, top_videos, videos_meta, top_traffic)

    resp = requests.post(os.environ["DISCORD_WEBHOOK_URL"], json={"content": message}, timeout=15)
    resp.raise_for_status()
    print("Posted to Discord:\n", message)


if __name__ == "__main__":
    main()
