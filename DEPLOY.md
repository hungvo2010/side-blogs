# Deploy to Hugging Face Spaces (Docker)

## Step 1: Create Space với Docker SDK
1. Vào https://huggingface.co/new-space?name=ai-blog-dashboard
2. **SDK: chọn Docker**
3. Blank template
4. Create

## Step 2: Clone Space về local
```bash
git clone https://huggingface.co/spaces/hungvo2010/ai-blog-dashboard
cd ai-blog-dashboard
```

## Step 3: Copy 2 files từ side-blogs repo
```bash
cp ~/side-projects/side-blogs/Dockerfile .
cp -r ~/side-projects/side-blogs/ai-blog-automation .
```

## Step 4: Set secrets trong HF Space UI
Vào Space → Settings → Repository secrets:
```
DATABASE_URL = postgresql://user:***@host.neon.tech/dbname?sslmode=require
OPENROUTER_API_KEY = sk-or-v1-***
ENVIRONMENT = production
```

## Step 5: Push
```bash
git add -A && git commit -m "init" && git push
```

Space tự build Docker image (~2-3 phút) → live.
