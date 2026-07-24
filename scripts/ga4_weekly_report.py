"""Fetch the last 7 days of GA4 data for gururi360 and post a summary to Discord.

Runs in GitHub Actions (see .github/workflows/ga4-weekly-report.yml).
Requires env vars: GA4_SERVICE_ACCOUNT_KEY (JSON string), GA4_PROPERTY_ID, DISCORD_WEBHOOK_URL.
"""

import json
import os

import requests
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)
from google.oauth2 import service_account

PROPERTY_ID = os.environ["GA4_PROPERTY_ID"]
DATE_RANGE = [DateRange(start_date="7daysAgo", end_date="today")]


def get_client():
    key_info = json.loads(os.environ["GA4_SERVICE_ACCOUNT_KEY"])
    creds = service_account.Credentials.from_service_account_info(key_info)
    return BetaAnalyticsDataClient(credentials=creds)


def fetch_totals(client):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=DATE_RANGE,
        metrics=[Metric(name="activeUsers"), Metric(name="newUsers"), Metric(name="sessions")],
    )
    resp = client.run_report(req)
    if not resp.rows:
        return "0", "0", "0"
    row = resp.rows[0]
    return row.metric_values[0].value, row.metric_values[1].value, row.metric_values[2].value


def fetch_top(client, dimension_name, metric_name, limit=5):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=DATE_RANGE,
        dimensions=[Dimension(name=dimension_name)],
        metrics=[Metric(name=metric_name)],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metric_name), desc=True)],
        limit=limit,
    )
    resp = client.run_report(req)
    return [(r.dimension_values[0].value, r.metric_values[0].value) for r in resp.rows]


def format_list(rows, empty_label="データなし"):
    if not rows:
        return empty_label
    return "\n".join(f"・{name}: {value}" for name, value in rows)


def build_message(active_users, new_users, sessions, channels, pages):
    return (
        "**📊 ぐるり360 週次レポート（直近7日間）**\n\n"
        f"アクティブユーザー: **{active_users}**\n"
        f"新規ユーザー: **{new_users}**\n"
        f"セッション数: **{sessions}**\n\n"
        "**流入チャネル TOP5**\n"
        f"{format_list(channels)}\n\n"
        "**ページ TOP5**\n"
        f"{format_list(pages)}"
    )


def main():
    client = get_client()
    active_users, new_users, sessions = fetch_totals(client)
    channels = fetch_top(client, "sessionDefaultChannelGroup", "sessions")
    pages = fetch_top(client, "pagePath", "screenPageViews")

    message = build_message(active_users, new_users, sessions, channels, pages)
    resp = requests.post(os.environ["DISCORD_WEBHOOK_URL"], json={"content": message}, timeout=15)
    resp.raise_for_status()
    print("Posted to Discord:", message)


if __name__ == "__main__":
    main()
