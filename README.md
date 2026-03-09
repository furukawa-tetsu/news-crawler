# AI Datacenter News Crawler 🤖

NewsAPI と RSS フィードから「AI datacenter / データセンター」関連ニュースを定期取得し、JSON に蓄積 + **RSS フィードを GitHub Pages で公開** → **Slack RSS App で通知** するクローラーです。

---

## 📁 ファイル構成

```
news-crawler/
├── crawler.py                        # メインクローラー
├── requirements.txt                  # 依存ライブラリ
├── news_data.json                    # 蓄積される全記事データ（自動生成）
├── docs/
│   ├── index.html                    # GitHub Pages トップ
│   └── news_feed.xml                 # Slack が購読する RSS（自動生成）
└── .github/
    └── workflows/
        └── crawl.yml                 # GitHub Actions ワークフロー
```

---

## 🔄 全体の流れ

```
GitHub Actions（毎日 09:00 / 18:00 JST）
  └── crawler.py 実行
        ├── NewsAPI からキーワード検索
        ├── RSS フィードをクロール
        ├── news_data.json に蓄積（重複排除）
        └── docs/news_feed.xml を生成
              └── GitHub Pages で公開
                    └── Slack RSS App が購読 → チャンネルに通知 🔔
```

---

## 📦 出力ファイル

### news_data.json（全記事蓄積）
```json
{
  "meta": {
    "last_updated": "2025-01-01T09:00:00+00:00",
    "total_count": 42
  },
  "articles": [
    {
      "id": "md5ハッシュ（重複排除用）",
      "source": "newsapi | rss:メディア名",
      "title": "記事タイトル",
      "summary": "記事の概要（最大300文字）",
      "url": "https://...",
      "published_at": "2025-01-01T08:00:00Z",
      "fetched_at": "2025-01-01T09:00:00+00:00",
      "keyword_matched": "AI datacenter"
    }
  ]
}
```

### docs/news_feed.xml（Slack 購読用 RSS）
最新50件を RSS 2.0 形式で出力。GitHub Pages 経由で公開されます。

---

## 🚀 セットアップ手順

### 1. GitHub リポジトリを作成して push

```bash
git init
git add .
git commit -m "init: news crawler"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. GitHub Pages を有効化

リポジトリの **Settings → Pages** を開き:
- **Source**: `Deploy from a branch`
- **Branch**: `main` / `docs` フォルダ を選択 → Save

公開 URL: `https://YOUR_USERNAME.github.io/YOUR_REPO/`

### 3. Secrets を登録

**Settings → Secrets and variables → Actions → New repository secret**

| Secret 名 | 内容 |
|---|---|
| `NEWSAPI_KEY` | [newsapi.org](https://newsapi.org) で取得（無料） |

### 4. 初回クロールを手動実行

Actions タブ → `AI Datacenter News Crawler` → `Run workflow`

RSS ファイルが生成されたことを確認:
`https://YOUR_USERNAME.github.io/YOUR_REPO/news_feed.xml`

### 5. Slack RSS App を設定

通知を受け取りたい Slack チャンネルで以下を入力するだけ:

```
/feed subscribe https://YOUR_USERNAME.github.io/YOUR_REPO/news_feed.xml
```

> 💡 管理者承認不要！チャンネルメンバーなら誰でも設定できます。

---

## ⏰ スケジュール変更

`crawl.yml` の cron 行を編集（UTC 基準）:

```yaml
- cron: "0 0 * * *"   # UTC 0:00 = JST 9:00
- cron: "0 9 * * *"   # UTC 9:00 = JST 18:00
```

> [crontab.guru](https://crontab.guru) で時刻を確認できます

---

## ➕ RSS フィード・キーワードの追加

`crawler.py` を直接編集してください:

```python
KEYWORDS = ["AI datacenter", "データセンター", "生成AI インフラ"]

RSS_FEEDS = [
    "https://example.com/rss.xml",
    ...
]
```
