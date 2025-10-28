# GitHub Secrets Configuration

Quick reference for all GitHub Secrets needed for the Algorythmos AI Content Scheduler.

Go to: **Settings → Secrets and variables → Actions → New repository secret**

---

## Required Secrets

| Secret Name | Example Format | Where to Get It |
|------------|----------------|-----------------|
| `NOTION_TOKEN` | `secret_abc123xyz...` | [Notion Integrations](https://www.notion.so/my-integrations) → Create integration |
| `NOTION_DB_ID` | `abc123def456...` | Your Notion database URL (32-char ID) |
| `X_API_KEY` | `abc123xyz...` | [Twitter Dev Portal](https://developer.twitter.com) → App → Keys and tokens |
| `X_API_SECRET` | `xyz789abc...` | Twitter Dev Portal → App → Keys and tokens |
| `X_ACCESS_TOKEN` | `123-abc...` | Twitter Dev Portal → App → Keys and tokens |
| `X_ACCESS_TOKEN_SECRET` | `def456xyz...` | Twitter Dev Portal → App → Keys and tokens |

### Alternative X Secret Names (Backward Compatible)

You can also use these names (old format):
- `API_KEY` instead of `X_API_KEY`
- `API_KEY_SECRET` instead of `X_API_SECRET`
- `ACCESS_TOKEN` instead of `X_ACCESS_TOKEN`
- `ACCESS_TOKEN_SECRET` instead of `X_ACCESS_TOKEN_SECRET`

---

## Optional Secrets (Enhanced Features)

| Secret Name | Example Format | Where to Get It |
|------------|----------------|-----------------|
| `OPENAI_API_KEY` | `sk-proj-abc123...` | [OpenAI API Keys](https://platform.openai.com/api-keys) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Leave blank to use default |
| `LINKEDIN_ACCESS_TOKEN` | `AQV...` | LinkedIn OAuth 2.0 (see SETUP.md) |
| `LINKEDIN_ORG_ID` | `12345678` | LinkedIn Company Page → About section |

---

## What Happens Without Optional Secrets?

### Without `OPENAI_API_KEY`
- ✅ System still works
- Uses heuristic fallback summarization
- Quality is lower but functional

### Without `LINKEDIN_ACCESS_TOKEN`
- ✅ System still works
- Posts only to X (Twitter)
- LinkedIn posting step is skipped

### Without `LINKEDIN_ORG_ID`
- ✅ System still works
- Posts to LinkedIn as personal profile
- Only needed for organization posts

---

## Verification

After adding all secrets, verify in GitHub:
1. Go to **Settings → Secrets and variables → Actions**
2. You should see all secrets listed (values are hidden)
3. Click **Update** to change a value
4. Never share secret values publicly

---

## Testing Secrets

### Test Locally (Development)
```bash
# Create .env file (DO NOT COMMIT)
cat > .env << EOF
NOTION_TOKEN=secret_abc123
NOTION_DB_ID=abc123def456
X_API_KEY=xxx
X_API_SECRET=xxx
X_ACCESS_TOKEN=xxx
X_ACCESS_TOKEN_SECRET=xxx
LINKEDIN_ACCESS_TOKEN=xxx
LINKEDIN_ORG_ID=12345678
OPENAI_API_KEY=sk-xxx
EOF

# Load into environment
export $(cat .env | xargs)

# Test
python fetch_ai_news.py --dry-run
```

### Test on GitHub Actions
1. Go to **Actions** tab
2. Select **AI Content Fetcher**
3. Click **Run workflow**
4. Check logs for any authentication errors

---

## Security Best Practices

- ✅ Never commit secrets to Git
- ✅ Add `.env` to `.gitignore`
- ✅ Rotate tokens every 90 days
- ✅ Use organization secrets for multiple repos
- ✅ Limit token permissions to minimum required
- ✅ Monitor GitHub security alerts

---

## Common Issues

### "NOTION_TOKEN is not set"
**Fix:** Add `NOTION_TOKEN` to GitHub Secrets

### "Twitter API authentication failed"
**Fix:** Verify all 4 X credentials are correct

### "LinkedIn 401 Unauthorized"
**Fix:** Access token expired, regenerate (60-day limit)

### "OpenAI API key invalid"
**Fix:** Check key format starts with `sk-`, verify billing

---

**Need Help?** See [SETUP.md](./SETUP.md) for detailed setup instructions.
