# 🚀 Algorythmos AI Content Scheduler - Deployment Checklist

Use this checklist to ensure your deployment is complete and working.

---

## ✅ Pre-Deployment Checklist

### 1. Repository Setup
- [ ] Repo forked/cloned to your GitHub account
- [ ] Repo renamed to `algorythmos-ai-content-scheduler` (optional)
- [ ] All files present:
  - [ ] `main.py`
  - [ ] `fetch_ai_news.py`
  - [ ] `check_ready_to_post.py`
  - [ ] `requirements.txt`
  - [ ] `README.md`
  - [ ] `SETUP.md`
  - [ ] `.github/workflows/fetch.yml`
  - [ ] `.github/workflows/post.yml`

### 2. Notion Configuration
- [ ] Notion integration created
- [ ] Integration token copied (`NOTION_TOKEN`)
- [ ] Database created with all required properties:
  - [ ] Tweet Content (Title)
  - [ ] Status (Select)
  - [ ] Scheduled Time (Date)
  - [ ] Posted Time (Date)
  - [ ] Tweet URL (URL)
  - [ ] LinkedIn URL (URL)
  - [ ] Media URLs (Text)
  - [ ] Error Message (Text)
  - [ ] Thread Group ID (Text) - optional
  - [ ] Thread Position (Number) - optional
- [ ] Integration connected to database
- [ ] Database ID copied (`NOTION_DB_ID`)

### 3. X (Twitter) API
- [ ] Developer account created
- [ ] App created with Read & Write permissions
- [ ] API Key copied (`X_API_KEY`)
- [ ] API Secret copied (`X_API_SECRET`)
- [ ] Access Token copied (`X_ACCESS_TOKEN`)
- [ ] Access Token Secret copied (`X_ACCESS_TOKEN_SECRET`)

### 4. LinkedIn API (Optional)
- [ ] LinkedIn Developer app created
- [ ] "Share on LinkedIn" product enabled
- [ ] OAuth access token obtained (`LINKEDIN_ACCESS_TOKEN`)
- [ ] Organization ID obtained (`LINKEDIN_ORG_ID`) - if posting as org

### 5. OpenAI API (Optional but Recommended)
- [ ] OpenAI account created
- [ ] API key generated (`OPENAI_API_KEY`)
- [ ] Billing credits added ($5-10 recommended)

### 6. GitHub Secrets
All secrets added to repository (Settings → Secrets → Actions):

**Required:**
- [ ] `NOTION_TOKEN`
- [ ] `NOTION_DB_ID`
- [ ] `X_API_KEY` (or `API_KEY`)
- [ ] `X_API_SECRET` (or `API_KEY_SECRET`)
- [ ] `X_ACCESS_TOKEN` (or `ACCESS_TOKEN`)
- [ ] `X_ACCESS_TOKEN_SECRET` (or `ACCESS_TOKEN_SECRET`)

**Optional:**
- [ ] `OPENAI_API_KEY`
- [ ] `OPENAI_MODEL` (defaults to `gpt-4o-mini`)
- [ ] `LINKEDIN_ACCESS_TOKEN`
- [ ] `LINKEDIN_ORG_ID`

---

## 🧪 Testing Checklist

### Local Testing (Recommended)

#### Test 1: Fetch (Dry Run)
```bash
python fetch_ai_news.py --dry-run
```
- [ ] Script runs without errors
- [ ] JSON output shows top article or "No fresh items"
- [ ] No writes to Notion

#### Test 2: Fetch (Real)
```bash
python fetch_ai_news.py
```
- [ ] Script runs without errors
- [ ] New row appears in Notion
- [ ] Status = "Scheduled"
- [ ] Tweet Content populated
- [ ] Scheduled Time is set
- [ ] Tweet URL and LinkedIn URL are empty

#### Test 3: X Poster
```bash
python main.py --platform x
```
- [ ] Script runs without errors
- [ ] Tweet posted to X
- [ ] Notion row updated:
  - [ ] Status = "Posted"
  - [ ] Posted Time set
  - [ ] Tweet URL populated
- [ ] Check X profile to verify post

#### Test 4: LinkedIn Poster
```bash
python main.py --platform linkedin
```
- [ ] Script runs without errors
- [ ] Post appears on LinkedIn
- [ ] Notion row updated:
  - [ ] LinkedIn URL populated
- [ ] Check LinkedIn profile to verify post

### GitHub Actions Testing

#### Test 5: Fetch Workflow
- [ ] Go to Actions → AI Content Fetcher → Run workflow
- [ ] Set `dry_run: false`
- [ ] Click Run workflow
- [ ] Workflow completes successfully (green ✓)
- [ ] Check logs for any errors
- [ ] Verify Notion has new scheduled entry

#### Test 6: Post Workflow (Manual)
- [ ] Go to Actions → Post to X & LinkedIn → Run workflow
- [ ] Click Run workflow
- [ ] Workflow completes successfully (green ✓)
- [ ] X step succeeds
- [ ] LinkedIn step succeeds (or skips if no token)
- [ ] Check Notion for updated URLs

---

## 📅 Automated Scheduling Checklist

### Verify Cron Jobs

#### Fetch Workflow
- [ ] Cron configured: `5 8 * 3-10 *` (CEST)
- [ ] Cron configured: `5 9 * 11,12,1,2 *` (CET)
- [ ] Should run at 10:05 AM Paris time

#### Post Workflow
- [ ] Cron configured: `10 8 * 3-10 *` (CEST)
- [ ] Cron configured: `10 9 * 11,12,1,2 *` (CET)
- [ ] Should run at 10:10 AM Paris time

### Wait for First Automated Run
- [ ] Wait until next scheduled time (10:05 AM Paris)
- [ ] Check Actions tab for automatic workflow run
- [ ] Verify fetch workflow ran
- [ ] Wait 5 minutes
- [ ] Verify post workflow ran
- [ ] Check X and LinkedIn for posts
- [ ] Check Notion for updated URLs

---

## 🎯 Success Criteria

Your deployment is successful when:

1. **Daily Operations:**
   - [ ] Fetch runs automatically at 10:05 AM Paris
   - [ ] Top AI news article is added to Notion
   - [ ] Post runs automatically at 10:10 AM Paris
   - [ ] Content posted to X (Twitter)
   - [ ] Content posted to LinkedIn (if configured)
   - [ ] URLs stored back in Notion

2. **Error Handling:**
   - [ ] If no fresh news, "Skipped" row created
   - [ ] If posting fails, Status = "Failed" with error message
   - [ ] If OpenAI fails, fallback summarization works

3. **Monitoring:**
   - [ ] GitHub Actions show green ✓ for successful runs
   - [ ] Notion database is organized and readable
   - [ ] Posts appear on social media within 5 minutes
   - [ ] No duplicate content

---

## 🐛 Troubleshooting Quick Reference

### Problem: "No scheduled posts due"
**Solution:** Check Notion database has entries with Status=Scheduled and Scheduled Time in the past

### Problem: X API authentication fails
**Solution:** Verify all 4 X credentials in GitHub Secrets, check app permissions

### Problem: LinkedIn 401 Unauthorized
**Solution:** Access token expired (60-day limit), regenerate token

### Problem: OpenAI rate limit
**Solution:** Check billing, add credits, or let fallback take over

### Problem: Workflow doesn't run on schedule
**Solution:** Check Actions tab is enabled, verify cron syntax, ensure repo is active

### Problem: "Import could not be resolved" locally
**Solution:** Run `pip install -r requirements.txt`

---

## 🎉 Post-Deployment

Once everything is working:

### 1. Documentation
- [ ] Update README.md with your specific details
- [ ] Add Algorythmos logo to repo
- [ ] Pin repo to profile (if public)

### 2. Customization
- [ ] Adjust RSS feeds in `fetch_ai_news.py`
- [ ] Modify BOOST_KEYWORDS for your niche
- [ ] Customize scoring weights
- [ ] Adjust posting time (cron schedule)

### 3. Monitoring
- [ ] Set up GitHub notifications for workflow failures
- [ ] Create Notion view for "Posted" items
- [ ] Track engagement metrics on X/LinkedIn

### 4. Scaling
- [ ] Add more RSS feeds
- [ ] Create multiple workflows for different topics
- [ ] Set up multiple LinkedIn/X accounts
- [ ] Add image generation (DALL-E integration)

---

## 📊 Expected Usage

### GitHub Actions Minutes
- **Fetch**: ~2 min/day = ~60 min/month
- **Post**: ~1 min/day = ~30 min/month
- **Total**: ~90 min/month (4.5% of free tier)

### OpenAI Costs
- **Model**: gpt-4o-mini
- **Usage**: 1 summary/day = ~30/month
- **Cost**: <$0.10/month

### Notion
- **Pages**: ~30/month
- **Cost**: Free tier

### Total Monthly Cost
- **$0.10/month** (virtually free!)

---

## ✅ Final Verification

Run through this final checklist:

1. [ ] All GitHub Secrets are set correctly
2. [ ] Notion database is configured with all properties
3. [ ] Local tests pass (fetch + post)
4. [ ] GitHub Actions tests pass
5. [ ] First automated run completed successfully
6. [ ] Posts appear on X and LinkedIn
7. [ ] URLs are stored in Notion
8. [ ] No errors in workflow logs
9. [ ] Documentation is updated
10. [ ] You understand how to monitor and troubleshoot

---

## 🎊 Congratulations!

Your **Algorythmos AI Content Scheduler** is now live and running! 🚀

You've built an enterprise-grade, fully automated AI content pipeline that:
- Curates the freshest AI news daily
- Summarizes with GPT-4o-mini
- Posts to X and LinkedIn automatically
- Tracks everything in Notion
- Costs less than a coffee per month

**What's Next?**
- Monitor for the first few days
- Tweak RSS feeds and scoring to your preference
- Scale to multiple accounts or topics
- Share your success with the community!

---

**Built with ❤️ by Algorythmos** | [algorythmos.fr](https://algorythmos.fr) | [@algorythmos](https://x.com/algorythmos)
