# ⚡ Quick Start Guide

Get your Algorythmos AI Content Scheduler running in **15 minutes**.

---

## 🎯 What You Need

Before starting, gather these:
- [ ] Notion account
- [ ] X (Twitter) Developer account
- [ ] GitHub account
- [ ] OpenAI API key (optional)

---

## 📝 5-Minute Setup Checklist

### Step 1: Notion (3 minutes)

1. Create integration: [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Copy integration token → Save as `NOTION_TOKEN`
3. Create database with these properties:
   - Tweet Content (Title)
   - Status (Select: Scheduled, Posted, Failed, Skipped)
   - Scheduled Time (Date with time)
   - Posted Time (Date with time)
   - Tweet URL (URL)
   - LinkedIn URL (URL)
   - Media URLs (Text)
   - Error Message (Text)
4. Connect integration to database (Share menu)
5. Copy database ID from URL → Save as `NOTION_DB_ID`

### Step 2: X/Twitter (3 minutes)

1. Go to [developer.twitter.com/portal](https://developer.twitter.com/en/portal/dashboard)
2. Create app with "Read and Write" permissions
3. Generate keys:
   - API Key → `X_API_KEY`
   - API Secret → `X_API_SECRET`
   - Access Token → `X_ACCESS_TOKEN`
   - Access Token Secret → `X_ACCESS_TOKEN_SECRET`

### Step 3: GitHub Secrets (2 minutes)

Go to **Settings → Secrets → Actions** and add:

**Required:**
```
NOTION_TOKEN
NOTION_DB_ID
X_API_KEY (or API_KEY)
X_API_SECRET (or API_KEY_SECRET)
X_ACCESS_TOKEN (or ACCESS_TOKEN)
X_ACCESS_TOKEN_SECRET (or ACCESS_TOKEN_SECRET)
```

**Optional:**
```
OPENAI_API_KEY (recommended)
LINKEDIN_ACCESS_TOKEN
LINKEDIN_ORG_ID
```

---

## 🧪 Test It (5 minutes)

### Option A: GitHub Actions (Easiest)

1. Go to **Actions** tab
2. Click **AI Content Fetcher**
3. Click **Run workflow**
4. Set `dry_run: false`
5. Wait ~2 minutes
6. Check your Notion database → Should see new entry
7. Click **Post to X & LinkedIn**
8. Click **Run workflow**
9. Wait ~1 minute
10. Check X and Notion → Should see post + URL

### Option B: Local Testing

```bash
# Clone repo
git clone YOUR_REPO_URL
cd algorythmos-ai-content-scheduler

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
NOTION_TOKEN=your_token_here
NOTION_DB_ID=your_db_id_here
X_API_KEY=your_key_here
X_API_SECRET=your_secret_here
X_ACCESS_TOKEN=your_token_here
X_ACCESS_TOKEN_SECRET=your_secret_here
OPENAI_API_KEY=your_openai_key_here
EOF

# Load environment
export $(cat .env | xargs)

# Test fetch
python fetch_ai_news.py --dry-run

# Should output JSON with article or "No fresh items"
```

---

## ✅ Verify It's Working

After setup, you should see:

### In Notion
- [ ] New database entry
- [ ] Status = "Scheduled"
- [ ] Tweet Content filled
- [ ] Scheduled Time in the past (for immediate posting)

### On X (Twitter)
- [ ] New tweet posted
- [ ] Same content as Notion

### Back in Notion
- [ ] Status changed to "Posted"
- [ ] Posted Time filled
- [ ] Tweet URL populated (clickable link to tweet)

---

## 🚀 Go Live

Once tested successfully:

1. **Automated runs start tomorrow**
   - 10:05 AM Paris: Fetches AI news
   - 10:10 AM Paris: Posts to X & LinkedIn

2. **Monitor in Actions tab**
   - Green ✓ = Success
   - Red ❌ = Check logs

3. **Check Notion daily**
   - Review what was posted
   - Check for errors

---

## 🆘 Troubleshooting

### "No scheduled posts due"
→ Check Notion has entry with Status=Scheduled and past Scheduled Time

### "Twitter API authentication failed"
→ Verify all 4 X credentials in GitHub Secrets

### "Import could not be resolved" (local only)
→ Run `pip install -r requirements.txt`

### Workflow doesn't run automatically
→ Check Actions tab is enabled in repo settings

---

## 📚 Need More Help?

- **Full Setup Guide**: [SETUP.md](./SETUP.md)
- **Deployment Checklist**: [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Secrets Reference**: [SECRETS.md](./SECRETS.md)
- **Transformation Details**: [TRANSFORMATION_SUMMARY.md](./TRANSFORMATION_SUMMARY.md)

---

## 🎉 Success!

If you see posts on X with URLs in Notion, **you're done**! 🚀

Your system will now:
- ✅ Automatically fetch AI news daily
- ✅ Score and summarize with GPT-4o-mini
- ✅ Post to X (Twitter)
- ✅ Post to LinkedIn (if configured)
- ✅ Track all URLs in Notion
- ✅ Cost you <$0.10/month

---

**Next Steps:**
1. Wait for tomorrow's automated run
2. Customize RSS feeds for your niche
3. Adjust scoring keywords
4. Add LinkedIn (see SETUP.md)
5. Scale to multiple accounts

---

**Built with ❤️ by Algorythmos** | [algorythmos.fr](https://algorythmos.fr) | [@algorythmos](https://x.com/algorythmos)
