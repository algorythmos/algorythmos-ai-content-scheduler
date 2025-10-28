# LinkedIn Token Setup Guide

Quick guide to generate your LinkedIn access token.

## Prerequisites

1. LinkedIn Developer Account
2. Created LinkedIn App with "Share on LinkedIn" product
3. LinkedIn Company Page (for organization posts)

## Step 1: Setup .env File

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your LinkedIn credentials:
# LINKEDIN_CLIENT_ID=78hiss1krq8y1
# LINKEDIN_CLIENT_SECRET=your_secret_here
# REDIRECT_URI=http://localhost:3000/auth/linkedin/callback
```

## Step 2: Install Dependencies

```bash
# Make sure python-dotenv is installed
pip install python-dotenv requests
```

## Step 3: Run Token Generator

### Option A: Using .env file (Recommended)

```bash
python get_linkedin_token.py
```

The script will:
1. Load credentials from `.env`
2. Open your browser to LinkedIn authorization
3. Ask you to paste the authorization code
4. Display your access token

### Option B: Using environment variables

```bash
# Set environment variables
export LINKEDIN_CLIENT_ID=78hiss1krq8y1
export LINKEDIN_CLIENT_SECRET=your_secret_here
export REDIRECT_URI=http://localhost:3000/auth/linkedin/callback

# Run script
python get_linkedin_token.py
```

## Step 4: Follow the Prompts

1. **Browser opens** to LinkedIn authorization page
2. **Click "Allow"** to authorize the app
3. **Copy the code** from the redirect URL (even if page shows error)
   - URL will look like: `http://localhost:3000/auth/linkedin/callback?code=AQT...&state=...`
   - Copy everything after `code=` and before `&`
4. **Paste the code** into the terminal
5. **Copy your access token** from the output

## Step 5: Save Tokens

### For Local Testing
Add to your `.env` file:
```bash
LINKEDIN_ACCESS_TOKEN=your_token_here
LINKEDIN_ORG_ID=your_org_id_here
```

### For GitHub Actions (Production)
Add to **Settings → Secrets → Actions**:
- `LINKEDIN_ACCESS_TOKEN` = your token
- `LINKEDIN_ORG_ID` = your organization ID

## Step 6: Get Organization ID

**Option A: From LinkedIn URL**
1. Go to your LinkedIn Company Page
2. URL looks like: `https://www.linkedin.com/company/algorythmos/`
3. The organization ID is the slug: `algorythmos`
4. Or click "About" to see numeric ID

**Option B: Using API**
```bash
# After getting access token
curl -H "Authorization: Bearer YOUR_TOKEN" \
     https://api.linkedin.com/v2/organizationalEntityAcls?q=roleAssignee
```

## Step 7: Test It

```bash
# Test posting to LinkedIn
python main.py --platform linkedin
```

## Troubleshooting

### "LINKEDIN_CLIENT_ID not set"
→ Make sure `.env` exists and has correct values
→ Or export environment variables manually

### "python-dotenv not installed"
→ Run: `pip install python-dotenv`
→ Or export variables manually (Option B above)

### "Error exchanging code for token"
→ Make sure redirect URI matches exactly in LinkedIn app settings
→ Code expires quickly - generate a new one

### Token expires after ~60 days
→ LinkedIn tokens expire regularly
→ Just run `python get_linkedin_token.py` again to refresh

## Security Notes

- ✅ `.env` is in `.gitignore` - never commit it
- ✅ Use GitHub Secrets for production
- ✅ Rotate tokens regularly
- ✅ Use organization tokens (not personal) for company posts

## Quick Reference

```bash
# Full workflow
cp .env.example .env          # Create .env
nano .env                     # Add credentials
pip install python-dotenv     # Install deps
python get_linkedin_token.py  # Generate token
# → Copy token to GitHub Secrets
python main.py --platform linkedin  # Test
```

---

**Need help?** See [SETUP.md](./SETUP.md) for full LinkedIn API setup instructions.
