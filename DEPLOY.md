# Side-Blogs — Build & Deploy Guide

Static blog trên Cloudflare Pages. Không database, không server, không WordPress.
Chỉ cần viết markdown → 1 lệnh build → deploy.

## Cấu trúc project

```
side-blogs/
├── public/                  # Static HTML output (Cloudflare Pages serve từ đây)
│   ├── index.html           # Home page (danh sách bài viết)
│   ├── posts.json           # Metadata index
│   ├── sitemap.xml
│   ├── robots.txt
│   ├── favicon.svg
│   ├── _redirects
│   ├── {slug}/index.html    # Mỗi bài viết 1 thư mục
│   └── about/index.html
│   └── privacy/index.html
├── content/                 # Markdown source (viết bài ở đây)
│   └── *.md
├── wrangler.toml            # Cloudflare Pages config
├── scripts/
│   ├── publish.py           # Build static site từ content/*.md
│   ├── publish_cf.py        # Build + upload thẳng lên Cloudflare API (ko cần git)
│   ├── fetch_images.py      # Backfill ảnh Unsplash vào frontmatter content/*.md
│   ├── gen_pages.py         # Tạo about/privacy pages
│   ├── run.py               # AI pipeline: research → draft → publish (full auto)
│   └── trending.py          # Lấy trending keywords
└── DEPLOY.md                # File này
```

> **⚠️ QUAN TRỌNG — project này KHÔNG auto-deploy từ git push.**
> Pages project `side-blogs` dùng ad-hoc deploy: phải chạy `wrangler pages deploy` hoặc
> `publish_cf.py` sau mỗi lần build. Git push chỉ lưu source, không kích hoạt deploy.
> Dấu hiệu nhận biết: trong Cloudflare dashboard, deployment type hiển thị "ad_hoc"
> thay vì "github".

## Prerequisites

Cài đặt 1 lần duy nhất:

```bash
# Python deps (dùng venv sẵn có của project)
cd ai-blog-automation
.venv/bin/python -m pip install -r requirements.txt

# Cloudflare wrangler CLI (để deploy)
npm install -g wrangler
# Hoặc dùng publish_cf.py (ko cần wrangler, chỉ cần API token)
```

## Cách thêm bài viết mới

### Cách 1: Viết markdown thủ công → build

```bash
# 1. Viết bài trong content/
nano content/my-new-post.md

# 2. Build + deploy 1 lệnh (publish.py tự gọi wrangler)
cd ai-blog-automation
SITE_NAME="The Slow Drip" SITE_URL="https://side-blogs.pages.dev" .venv/bin/python scripts/publish.py
```

### Cách 2: Dùng AI pipeline (full auto)

```bash
cd ai-blog-automation
.venv/bin/python scripts/run.py "your keyword"
```

Tự động: research keyword → tạo brief → viết draft → fact check → SEO → fetch ảnh → publish.

Cần env: `OPENROUTER_API_KEY`, `DATABASE_URL` (Neon postgres).

### Cách 3: Single post từ file markdown

```bash
cd ai-blog-automation
SITE_NAME="The Slow Drip" SITE_URL="https://side-blogs.pages.dev" .venv/bin/python scripts/publish.py my-post.md -t "Post Title" --tags "coffee,guide"
```

## Cách deploy

### Option A: publish.py (build + deploy 1 lệnh, default)

`publish.py` tự gọi `wrangler pages deploy` sau khi build — **không cần git push, không cần bước riêng**.

```bash
cd ai-blog-automation
SITE_NAME="The Slow Drip" SITE_URL="https://side-blogs.pages.dev" .venv/bin/python scripts/publish.py
```

- Bỏ `--no-push` để deploy (default là deploy luôn)
- `--no-push` = build only, không deploy
- ⚠️ Luôn pass `SITE_NAME` + `SITE_URL` từ shell — publish.py đọc từ `os.environ`, KHÔNG đọc `.env`
- Cần `wrangler login` 1 lần (xem Option B)

### Option B: wrangler CLI (deploy riêng sau khi build)

```bash
wrangler login
wrangler pages deploy public --project-name=side-blogs --branch=main --commit-dirty=true
```

### Option C: publish_cf.py (dùng API token, ko cần wrangler/git)

```bash
export CLOUDFLARE_API_TOKEN="your-token"
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export CLOUDFLARE_PROJECT_NAME="side-blogs"

cd ai-blog-automation
.venv/bin/python scripts/publish_cf.py
```

Lấy token tại: https://dash.cloudflare.com/profile/api-tokens → Create Token → Custom → Cloudflare Pages:Edit.

## Cách update bài viết đã có

```bash
# 1. Sửa file markdown trong content/
nano content/my-post.md

# 2. Build + deploy lại
cd ai-blog-automation
SITE_NAME="The Slow Drip" SITE_URL="https://side-blogs.pages.dev" .venv/bin/python scripts/publish.py
```

## Ảnh trên homepage

Homepage hiển thị thumbnail cho mỗi bài viết nếu frontmatter có `image:`.

### Lấy ảnh Unsplash cho bài chưa có

```bash
cd ai-blog-automation
# .env phải có UNSPLASH_ACCESS_KEY (hoặc IMAGE_PROVIDER=unsplash)
.venv/bin/python scripts/fetch_images.py
```

Script này tự tìm ảnh theo title bài, chèn `image:` vào frontmatter của mọi file
`content/*.md` chưa có ảnh. Chạy xong → build + deploy lại.

Hoặc tự thêm thủ công vào đầu file markdown:

```yaml
---
title: Bài viết của tôi
image: https://images.unsplash.com/photo-xxxx?w=200
---
```

### Ảnh thumbnails 120x90 (desktop) / full-width (mobile)

Template homepage trong `scripts/publish.py` (INDEX_TEMPLATE + build_index).
Muốn đổi kích thước/kiểu ảnh → sửa CSS `.posts .thumb` trong đó.

## Environment variables

Để trong `ai-blog-automation/.env`:

| Variable | Required | Description |
|---|---|---|
| `SITE_NAME` | No (default: "My Blog") | Tên blog |
| `SITE_URL` | No (default: "https://myblog.pages.dev") | URL blog |
| `SITE_AUTHOR` | No (default: "Anonymous") | Tên tác giả |
| `SITE_DESCRIPTION` | No | Mô tả homepage |
| `SITE_LANG` | No (default: "en") | Ngôn ngữ |
| `UNSPLASH_ACCESS_KEY` | Cho ảnh homepage | Unsplash API key (50 req/h free) |
| `IMAGE_PROVIDER` | No (default: pexels) | unsplash / pexels / pixabay |
| `PEXELS_API_KEY` | No | Pexels API key (200 req/h free) |
| `OPENROUTER_API_KEY` | Cho AI pipeline | OpenRouter API key |
| `DATABASE_URL` | Cho AI pipeline | Neon postgres URL |
| `CLOUDFLARE_API_TOKEN` | Cho publish_cf.py | Cloudflare Pages API token |
| `CLOUDFLARE_ACCOUNT_ID` | Cho publish_cf.py | Cloudflare account ID |
| `CLOUDFLARE_PROJECT_NAME` | Cho publish_cf.py | Tên Pages project |

## Static pages (About, Privacy)

```bash
cd ai-blog-automation
.venv/bin/python scripts/gen_pages.py
```

Kết quả trong `public/about/index.html` và `public/privacy/index.html`.
Muốn đổi nội dung → sửa trực tiếp trong `gen_pages.py`.

## Lưu ý

- **public/** là thư mục output, đừng sửa file trong đó (sẽ bị overwrite khi build).
- Chỉ sửa markdown trong **content/** hoặc script trong **scripts/**.
- publish.py build toàn bộ content/*.md mỗi lần chạy → xóa bài cũ bằng cách xóa file .md rồi build lại.
- Không cần database nếu chỉ dùng publish.py (database chỉ cần cho AI pipeline với run.py).
