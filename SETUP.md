# Algorythmos AI Content Scheduler - Complete Setup Guide

## 🎯 Overview

This guide walks you through setting up the **Algorythmos AI Content Scheduler** from scratch. You'll configure:
- ✅ Notion database with required properties
- ✅ X (Twitter) API credentials
- ✅ LinkedIn API credentials
- ✅ OpenAI API key
- ✅ GitHub Secrets
- ✅ Testing & deployment

---

## 📋 Prerequisites

- GitHub account (free tier is sufficient)
- Notion account (free tier is sufficient)
- X (Twitter) Developer account
- LinkedIn Developer account
- OpenAI API account (optional but recommended)

---

## Step 1: Create Notion Database

### 1.1 Create Integration

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **"+ New integration"**
3. Name: `Algorythmos Content Scheduler`
4. Select your workspace
5. Copy the **Internal Integration Token** (starts with `secret_`)
6. Save this as `NOTION_TOKEN`

### 1.2 Create Database

1. Create a new page in Notion
2. Add a **Database - Full page**
3. Name it: `AI Content Queue`

### 1.3 Add Required Properties

Add these properties to your database (exact names are important):

| Property Name | Type | Description |
|--------------|------|-------------|
| `Tweet Content` | Title | The text to post |
| `Status` | Select | Options: `Scheduled`, `Posted`, `Failed`, `Skipped` |
| `Scheduled Time` | Date | When to post (with time) |
| `Posted Time` | Date | When it was posted |
| `Tweet URL` | URL | Link to posted tweet |
| `LinkedIn URL` | URL | Link to posted LinkedIn post |
| `Media URLs` | Text | URLs of images/media to attach |
| `Error Message` | Text | Error details if failed |
| `Thread Group ID` | Text | For threading (optional) |
| `Thread Position` | Number | Position in thread (optional) |

### 1.4 Connect Integration to Database

1. Click the **•••** menu in your database
2. Select **"Connections"**
3. Add your **Algorythmos Content Scheduler** integration

### 1.5 Get Database ID

From your database URL:
```
https://notion.so/workspace/abc123def456?v=...
                        ^^^^^^^^^^^^^^^^
                        This is your Database ID
```

Or from Share menu → Copy link → Extract the 32-character ID

Save this as `NOTION_DB_ID`

---

## Step 2: X (Twitter) API Setup

### 2.1 Create Developer Account

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Sign up for Developer Account (free tier)
3. Complete the application form

### 2.2 Create App

1. Click **"+ Create App"**
2. Name: `Algorythmos AI Scheduler`
3. Set App Permissions to: **Read and Write**

### 2.3 Generate Credentials

1. Go to **Keys and tokens** tab
2. Generate/copy these values:
   - **API Key** → Save as `X_API_KEY` (or `API_KEY`)
   - **API Secret Key** → Save as `X_API_SECRET` (or `API_KEY_SECRET`)
   - **Access Token** → Save as `X_ACCESS_TOKEN` (or `ACCESS_TOKEN`)
   - **Access Token Secret** → Save as `X_ACCESS_TOKEN_SECRET` (or `ACCESS_TOKEN_SECRET`)

⚠️ **Important**: Keep these secret! Never commit them to Git.

---

## Step 3: LinkedIn API Setup

### 3.1 Create LinkedIn App

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/apps)
2. Click **"Create app"**
3. Fill in details:
   - App name: `Algorythmos AI Scheduler`
   - LinkedIn Page: Select your company page (or create one)
   - App logo: Upload Algorythmos logo
   - Accept terms

### 3.2 Configure Products

1. In your app, go to **Products** tab
2. Request access to: **Share on LinkedIn**
3. Request access to: **Sign In with LinkedIn** (if posting as user)

### 3.3 Get Access Token

**Option A: Organization Posts (Recommended)**

1. Go to **Auth** tab
2. Copy **Client ID** and **Client Secret**
3. Add OAuth 2.0 redirect URL: `https://localhost/callback`
4. Use OAuth 2.0 flow to get access token (see below)
5. Get your organization ID from LinkedIn Page → About → Company ID
6. Save token as `LINKEDIN_ACCESS_TOKEN`
7. Save org ID as `LINKEDIN_ORG_ID`

**Option B: Personal Posts**

1. Same as above, but omit `LINKEDIN_ORG_ID`
2. Posts will be from your personal profile

**Getting Access Token (Manual OAuth Flow)**

```bash
# 1. Build authorization URL (replace CLIENT_ID)
https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=https://localhost/callback&scope=w_member_social

# 2. Open in browser → Authorize → Copy 'code' parameter from redirect URL

# 3. Exchange code for token (replace values)
curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
  -d grant_type=authorization_code \
  -d code=YOUR_CODE \
  -d redirect_uri=https://localhost/callback \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET

# 4. Copy 'access_token' from response
```

---

## Step 4: OpenAI API Setup

### 4.1 Create API Key

1. Go to [OpenAI API Keys](https://platform.openai.com/api-keys)
2. Click **"+ Create new secret key"**
3. Name: `Algorythmos Content Scheduler`
4. Copy the key (starts with `sk-`)
5. Save as `OPENAI_API_KEY`

### 4.2 Add Credits

1. Go to [Billing](https://platform.openai.com/account/billing/overview)
2. Add $5-10 credit (will last months with gpt-4o-mini)

⚠️ **Optional**: If you skip this, the system will use fallback heuristic summarization (still works!)

---

## Step 5: Configure GitHub Secrets

### 5.1 Add Repository Secrets

1. Go to your GitHub repo
2. Navigate to **Settings → Secrets and variables → Actions**
3. Click **"New repository secret"** for each:

**Required Secrets:**

| Secret Name | Value | Source |
|------------|-------|--------|
| `NOTION_TOKEN` | `secret_xxx...` | Notion Integration (Step 1.1) |
| `NOTION_DB_ID` | `abc123def456...` | Notion Database ID (Step 1.5) |
| `X_API_KEY` or `API_KEY` | Your X API Key | Twitter Dev Portal (Step 2.3) |
| `X_API_SECRET` or `API_KEY_SECRET` | Your X API Secret | Twitter Dev Portal (Step 2.3) |
| `X_ACCESS_TOKEN` or `ACCESS_TOKEN` | Your X Access Token | Twitter Dev Portal (Step 2.3) |
| `X_ACCESS_TOKEN_SECRET` or `ACCESS_TOKEN_SECRET` | Your X Access Token Secret | Twitter Dev Portal (Step 2.3) |

**Optional Secrets:**

| Secret Name | Value | Source |
|------------|-------|--------|
| `LINKEDIN_ACCESS_TOKEN` | OAuth token | LinkedIn OAuth (Step 3.3) |
| `LINKEDIN_ORG_ID` | Company ID | LinkedIn Page (Step 3.3) |
| `OPENAI_API_KEY` | `sk-xxx...` | OpenAI Platform (Step 4.1) |

---

## Step 6: Test the Setup

### 6.1 Local Testing (Recommended)

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/algorythmos-ai-content-scheduler.git
cd algorythmos-ai-content-scheduler

# Install dependencies
pip install -r requirements.txt

# Set environment variables (create .env file)
cat > .env << EOF
NOTION_TOKEN=secret_xxx
NOTION_DB_ID=abc123def456
X_API_KEY=xxx
X_API_SECRET=xxx
X_ACCESS_TOKEN=xxx
X_ACCESS_TOKEN_SECRET=xxx
LINKEDIN_ACCESS_TOKEN=xxx
LINKEDIN_ORG_ID=12345678
OPENAI_API_KEY=sk-xxx
EOF

# Load .env
export $(cat .env | xargs)

# Test fetcher (dry run - doesn't write to Notion)
python fetch_ai_news.py --dry-run

# Expected output: JSON with top article or "No fresh items"

# Test fetcher (real run - writes to Notion)
python fetch_ai_news.py

# Check your Notion database - should see new "Scheduled" entry

# Test X poster
python main.py --platform x

# Test LinkedIn poster
python main.py --platform linkedin
```

### 6.2 GitHub Actions Testing

1. Go to **Actions** tab in your repo
2. Select **AI Content Fetcher** workflow
3. Click **Run workflow**
4. Set `dry_run: false`
5. Click **Run workflow** button
6. Check logs and Notion database

---

## Step 7: Enable Automated Scheduling

The workflows are already configured to run automatically:

- **Fetcher**: Daily at 10:05 AM Paris time
- **Poster**: Daily at 10:10 AM Paris time (5 min after fetcher)

### Verify Schedule

1. Go to **Actions** tab
2. Click on workflow name
3. You'll see "This workflow has a workflow_dispatch event trigger"
4. Check that scheduled runs appear in the runs list

---

## 🎉 You're Done!

Your Algorythmos AI Content Scheduler is now:
- ✅ Fetching AI news daily
- ✅ Scoring and summarizing with GPT-4o-mini
- ✅ Queuing in Notion
- ✅ Auto-posting to X (Twitter)
- ✅ Auto-posting to LinkedIn
- ✅ Storing post URLs back in Notion

---

## 🔧 Troubleshooting

### "No scheduled posts due"
- Check Notion database has entries with `Status=Scheduled`
- Verify `Scheduled Time` is in the past
- Run `python check_ready_to_post.py` to debug

### X API Errors
- Verify all 4 X credentials are set correctly
- Check App permissions are "Read and Write"
- Ensure tokens haven't expired

### LinkedIn API Errors
- Check access token hasn't expired (LinkedIn tokens expire after 60 days)
- Verify app has "Share on LinkedIn" product enabled
- For org posts, ensure `LINKEDIN_ORG_ID` is correct

### OpenAI Errors
- Check API key is valid
- Verify billing is set up
- Fallback will activate automatically if OpenAI fails

### Notion Errors
- Verify integration is connected to database
- Check all required properties exist with correct names
- Ensure property types match (Text, Select, URL, etc.)

---

## 📊 Monitoring

### GitHub Actions
- Go to **Actions** tab to see all runs
- Click on a run to see detailed logs
- Failed runs will show red ❌
- Successful runs will show green ✓

### Notion Database
- `Status` column shows current state
- `Error Message` shows what went wrong
- `Tweet URL` and `LinkedIn URL` link to posts

---

## 🚀 Next Steps

1. **Add more RSS feeds**: Edit `RSS_FEEDS` list in `fetch_ai_news.py`
2. **Customize scoring**: Adjust `BOOST_KEYWORDS` and scoring logic
3. **Add images**: RSS feeds with `media_content` will auto-attach images
4. **Thread support**: Use `Thread Group ID` and `Thread Position` properties
5. **Multiple accounts**: Duplicate workflows with different secrets

---

## 📞 Support

- Issues: [GitHub Issues](https://github.com/skalaliya/algorythmos-ai-content-scheduler/issues)
- Email: info@algorythmos.fr
- Website: [algorythmos.fr](https://algorythmos.fr)

---

**Built with ❤️ by Algorythmos** | France Remote Worldwide
