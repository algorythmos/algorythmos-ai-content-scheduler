# 🚀 Algorythmos AI Content Scheduler - Setup Guide

## Current Status

✅ **Code Complete** - All features implemented and tested
✅ **Documentation Complete** - README with full instructions
✅ **Repository Configured** - 9/10 GitHub Secrets added
⚠️ **Action Required** - Add `GH_PAT` secret to enable automatic workflow chaining

---

## 🎯 Final Setup Step: Add GH_PAT

The workflow chaining feature is fully implemented but requires a GitHub Personal Access Token (PAT) with `workflow` scope to function.

### Why GH_PAT is Required

GitHub's default `GITHUB_TOKEN` cannot trigger other workflows due to security restrictions. This is intentional to prevent recursive workflow triggers. To enable the **Content Aggregator** to automatically trigger the **Social Publisher**, you need a PAT.

### Step-by-Step Instructions

#### 1. Generate Personal Access Token

1. **Open GitHub Token Generator:**
   ```
   https://github.com/settings/tokens/new
   ```

2. **Configure Token:**
   - **Note:** `Algorythmos Content Scheduler - Workflow Trigger`
   - **Expiration:** `90 days` (or `No expiration` if you want to set it and forget it)
   - **Scopes:** Check **ONLY** `workflow` (no other scopes needed)

3. **Generate and Copy:**
   - Click **"Generate token"**
   - Copy the token (starts with `ghp_...`)
   - ⚠️ **Important:** Save it somewhere safe! You won't be able to see it again.

#### 2. Add Token to Repository Secrets

1. **Navigate to Secrets Settings:**
   ```
   https://github.com/algorythmos/algorythmos-ai-content-scheduler/settings/secrets/actions
   ```

2. **Add New Secret:**
   - Click **"New repository secret"**
   - **Name:** `GH_PAT`
   - **Value:** Paste the token you copied (e.g., `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`)
   - Click **"Add secret"**

3. **Verify:**
   - You should now see `GH_PAT` in your list of secrets
   - Total secrets: **10/10** ✅

#### 3. Test the Workflow

1. **Navigate to Actions:**
   ```
   https://github.com/algorythmos/algorythmos-ai-content-scheduler/actions
   ```

2. **Manually Trigger Content Aggregator:**
   - Click **"📰 Algorythmos Content Aggregator"**
   - Click **"Run workflow"** dropdown
   - Set `dry_run` to `false`
   - Click **"Run workflow"** button

3. **Observe Automatic Chaining:**
   - Content Aggregator completes successfully
   - Waits 30 seconds for Notion sync
   - Automatically triggers Social Publisher
   - Social Publisher posts to X and LinkedIn
   - Both platforms' URLs are saved back to Notion

#### Expected Logs (Success)

**Content Aggregator → Trigger Publisher Job:**
```
⏳ Waiting 30 seconds for Notion to sync...
✅ Wait complete
🚀 Triggering Social Publisher workflow...
   Repository: algorythmos/algorythmos-ai-content-scheduler
   Workflow: post.yml
   Branch: main
📊 Response Status: 204
✅ Successfully triggered Social Publisher workflow!
```

**Social Publisher:**
```
🚀 Publishing to X...
✅ Posted to X successfully
🚀 Publishing to LinkedIn...
✅ Posted to LinkedIn successfully
✅ Updated Notion with X and LinkedIn URLs
```

---

## 📋 Complete Secrets Checklist

| Secret | Status | Description |
|--------|--------|-------------|
| `NOTION_TOKEN` | ✅ | Notion integration token |
| `NOTION_DB_ID` | ✅ | Notion database ID |
| `X_API_KEY` | ✅ | X/Twitter API key |
| `X_API_SECRET` | ✅ | X/Twitter API secret |
| `X_ACCESS_TOKEN` | ✅ | X/Twitter access token |
| `X_ACCESS_TOKEN_SECRET` | ✅ | X/Twitter access token secret |
| `LINKEDIN_ACCESS_TOKEN` | ✅ | LinkedIn OAuth access token |
| `LINKEDIN_CLIENT_ID` | ✅ | LinkedIn app client ID |
| `LINKEDIN_CLIENT_SECRET` | ✅ | LinkedIn app client secret |
| `GH_PAT` | ⚠️ **NEEDS SETUP** | GitHub PAT with `workflow` scope |

### Optional Secrets

| Secret | Status | Description |
|--------|--------|-------------|
| `OPENAI_API_KEY` | ⚠️ Optional | OpenAI API key (uses fallback if missing) |
| `OPENAI_MODEL` | ⚠️ Optional | Override model (default: `gpt-4o-mini`) |

---

## 🔧 Troubleshooting

### Issue: 403 Error on Workflow Trigger

**Symptom:**
```
❌ Failed to trigger workflow. Status code: 403
Resource not accessible by integration
```

**Cause:** `GH_PAT` secret is missing or has insufficient permissions.

**Solution:**
1. Verify `GH_PAT` secret exists in repository settings
2. Ensure PAT has `workflow` scope checked
3. Check PAT hasn't expired (generate new one if needed)
4. Retry workflow

---

### Issue: PAT Expired

**Symptom:** Workflow trigger fails with authentication error after 90 days.

**Solution:**
1. Generate new PAT (follow steps above)
2. Update `GH_PAT` secret with new token
3. No code changes needed

---

### Issue: No Automatic Triggering

**Symptom:** Content Aggregator completes but Social Publisher doesn't start.

**Checklist:**
- [ ] `GH_PAT` secret is added
- [ ] Workflow ran with `dry_run=false` (dry runs don't trigger)
- [ ] Content Aggregator job completed successfully
- [ ] Check Actions logs for "Trigger Social Publisher" job

---

## 🎉 What Happens After Setup

Once `GH_PAT` is configured, the system runs fully autonomously:

### Daily Schedule (Europe/Paris Time)

**10:05 AM** - Content Aggregator runs:
- Fetches AI news from 7 sources
- Scores by relevance + recency
- Summarizes with GPT-4o-mini (or fallback)
- Creates Notion entry with `Status=Scheduled`

**10:05 AM + 30 seconds** - Automatic trigger:
- Content Aggregator waits for Notion sync
- Triggers Social Publisher via GitHub API

**10:05 AM + 31 seconds** - Social Publisher runs:
- Fetches scheduled posts from Notion
- Posts to X (Twitter) and LinkedIn
- Updates Notion with post URLs
- Sets `Status=Posted`

**10:10 AM** - Backup schedule:
- Social Publisher also runs on independent schedule
- Acts as fallback if auto-trigger fails

### Monthly Cost

- **GitHub Actions:** ~90 minutes/month (4.5% of free tier)
- **OpenAI API:** ~$0.003/month (negligible)
- **X API:** Free tier (30/1500 posts)
- **LinkedIn API:** Free tier (30/3000 posts)
- **Notion API:** Free (unlimited)

**Total:** Essentially **free** ✨

---

## 📚 Additional Resources

- **Full Documentation:** [README.md](README.md)
- **Repository:** https://github.com/algorythmos/algorythmos-ai-content-scheduler
- **Notion Template:** Create your own database with required properties (see README)
- **LinkedIn Token Generator:** `get_linkedin_token.py` (run locally)

---

## ✅ Setup Complete!

Once you've added the `GH_PAT` secret and tested successfully, your AI Content Scheduler is fully operational! 🚀

The system will now:
- ✅ Run daily at 10:05 AM Paris time
- ✅ Automatically aggregate AI news
- ✅ Summarize with AI
- ✅ Queue in Notion
- ✅ Auto-trigger publishing
- ✅ Post to X and LinkedIn
- ✅ Track URLs
- ✅ Handle errors gracefully

**No further action required** - just monitor the Actions tab and enjoy automated content! 🎉
