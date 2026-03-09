"""
AI Datacenter News Crawler
- Sources: NewsAPI + RSS feeds
- Keywords: "AI datacenter", "データセンター"
- Output: JSON accumulation + RSS feed (for Slack RSS App)
"""

import json
import os
import hashlib
import feedparser
import requests
from datetime import datetime, timezone
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

# ── 設定 ──────────────────────────────────────────────
KEYWORDS = ["AI datacenter", "data center AI", "データセンター"]

RSS_FEEDS = [
    # Tech / AI
    "https://feeds.feedburner.com/TechCrunch",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.wired.com/feed/rss",
    "https://venturebeat.com/feed/",
    # Data Center 専門
    "https://www.datacenterknowledge.com/rss.xml",
    "https://www.datacenterdynamics.com/en/rss/",
    # 日本語
    "https://news.yahoo.co.jp/rss/topics/it.xml",
    "https://www.itmedia.co.jp/rss/2.0/news_bursts.xml",
]

OUTPUT_FILE = Path(os.getenv("OUTPUT_FILE", "news_data.json"))
# GitHub Pages で公開される RSS ファイルのパス（docs/ 配下）
RSS_OUTPUT_FILE = Path(os.getenv("RSS_OUTPUT_FILE", "docs/news_feed.xml"))
# GitHub Pages の公開 URL（crawl.yml の GITHUB_PAGES_URL env で設定）
GITHUB_PAGES_URL = os.getenv("GITHUB_PAGES_URL", "https://YOUR_USERNAME.github.io/YOUR_REPO")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


# ── ユーティリティ ────────────────────────────────────
def make_id(url: str) -> str:
    """URLからユニークIDを生成（重複排除用）"""
    return hashlib.md5(url.encode()).hexdigest()


def keyword_match(text: str) -> bool:
    """いずれかのキーワードにマッチするか"""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in KEYWORDS)


def load_existing(path: Path) -> dict:
    """既存JSONを読み込む"""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"articles": [], "meta": {"last_updated": None, "total_count": 0}}


def save_data(path: Path, data: dict):
    """JSONに保存"""
    data["meta"]["last_updated"] = datetime.now(timezone.utc).isoformat()
    data["meta"]["total_count"] = len(data["articles"])
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── NewsAPI ───────────────────────────────────────────
def fetch_newsapi() -> list[dict]:
    if not NEWSAPI_KEY:
        print("[NewsAPI] NEWSAPI_KEY が未設定のためスキップ")
        return []

    articles = []
    for keyword in ["AI datacenter", "データセンター"]:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": keyword,
            "sortBy": "publishedAt",
            "pageSize": 20,
            "language": "en",  # "jp" は未対応のため en
            "apiKey": NEWSAPI_KEY,
        }
        try:
            res = requests.get(url, params=params, timeout=10)
            res.raise_for_status()
            for a in res.json().get("articles", []):
                articles.append({
                    "id": make_id(a.get("url", "")),
                    "source": "newsapi",
                    "title": a.get("title", ""),
                    "summary": a.get("description", "") or "",
                    "url": a.get("url", ""),
                    "published_at": a.get("publishedAt", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "keyword_matched": keyword,
                })
        except Exception as e:
            print(f"[NewsAPI] エラー ({keyword}): {e}")

    print(f"[NewsAPI] {len(articles)} 件取得")
    return articles


# ── RSS ───────────────────────────────────────────────
def fetch_rss() -> list[dict]:
    articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "") or entry.get("description", "") or ""
                link = entry.get("link", "")
                published = entry.get("published", "") or entry.get("updated", "")

                # キーワードチェック（タイトル or サマリ）
                if not keyword_match(title + " " + summary):
                    continue

                matched_kw = next(
                    (kw for kw in KEYWORDS if kw.lower() in (title + summary).lower()), ""
                )
                articles.append({
                    "id": make_id(link),
                    "source": f"rss:{feed.feed.get('title', feed_url)}",
                    "title": title,
                    "summary": summary[:300] + ("..." if len(summary) > 300 else ""),
                    "url": link,
                    "published_at": published,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "keyword_matched": matched_kw,
                })
        except Exception as e:
            print(f"[RSS] エラー ({feed_url}): {e}")

    print(f"[RSS] {len(articles)} 件取得（キーワードマッチ）")
    return articles


# ── 重複排除 & マージ ─────────────────────────────────
def merge_articles(existing: dict, new_articles: list[dict]) -> tuple[dict, list[dict]]:
    existing_ids = {a["id"] for a in existing["articles"]}
    added = []
    for article in new_articles:
        if article["id"] not in existing_ids:
            existing["articles"].append(article)
            existing_ids.add(article["id"])
            added.append(article)
    # 最新順に並べ替え
    existing["articles"].sort(key=lambda x: x.get("published_at", ""), reverse=True)
    return existing, added


# ── RSS フィード生成 ──────────────────────────────────
def generate_rss(articles: list[dict], output_path: Path):
    """
    最新50件を Atom/RSS2.0 形式で出力。
    Slack RSS App はこのファイルを定期ポーリングして通知する。
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = "AI Datacenter News"
    SubElement(channel, "link").text = GITHUB_PAGES_URL
    SubElement(channel, "description").text = (
        "AI datacenter / データセンター 関連ニュースの自動収集フィード"
    )
    SubElement(channel, "language").text = "ja"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    for article in articles[:50]:  # 最新50件
        item = SubElement(channel, "item")
        SubElement(item, "title").text = article.get("title") or "(タイトルなし)"
        SubElement(item, "link").text = article.get("url", "")
        SubElement(item, "description").text = article.get("summary", "")
        SubElement(item, "guid", isPermaLink="false").text = article.get("id", "")
        SubElement(item, "source").text = article.get("source", "")
        # pubDate: RFC 2822 形式に変換（可能な場合）
        pub = article.get("published_at", "")
        SubElement(item, "pubDate").text = pub

    # 整形して書き出し
    xml_str = minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ")
    # minidom が追加する余分な宣言行を除去
    xml_lines = [l for l in xml_str.splitlines() if l.strip()]
    xml_out = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(xml_lines[1:])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_out)

    print(f"[RSS生成] {output_path} に {min(len(articles), 50)} 件を出力")


# ── メイン ────────────────────────────────────────────
def main():
    print(f"=== クロール開始: {datetime.now(timezone.utc).isoformat()} ===")

    # 既存データ読み込み
    data = load_existing(OUTPUT_FILE)
    print(f"既存記事数: {len(data['articles'])} 件")

    # 取得
    all_new = fetch_newsapi() + fetch_rss()

    # マージ（重複排除）
    data, added = merge_articles(data, all_new)
    print(f"新規追加: {len(added)} 件 / 合計: {len(data['articles'])} 件")

    # JSON 保存
    save_data(OUTPUT_FILE, data)
    print(f"JSONに保存: {OUTPUT_FILE}")

    # RSS フィード生成（GitHub Pages で公開 → Slack が購読）
    generate_rss(data["articles"], RSS_OUTPUT_FILE)

    print("=== クロール完了 ===")


if __name__ == "__main__":
    main()
