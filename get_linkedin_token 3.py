#!/usr/bin/env python3# get_linkedin_token.py

"""from requests_oauthlib import OAuth2Session

LinkedIn OAuth 2.0 Token Generatorimport os, webbrowser

Generates access tokens for LinkedIn API with organization posting permissions.

# Load from environment

Usage:client_id = os.getenv("LINKEDIN_CLIENT_ID")

    1. Add credentials to .env fileclient_secret = os.getenv("LINKEDIN_CLIENT_SECRET")

    2. Run: python get_linkedin_token.pyredirect_uri = "http://localhost:3000/auth/linkedin/callback"

    3. Follow the authorization URL in your browser

    4. Paste the code from redirect URL# Scopes: company posts + profile + refresh

    5. Copy the access token to GitHub Secretsscopes = ["w_organization_social", "r_liteprofile", "offline_access"]

"""

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)

import osauth_url, _ = oauth.authorization_url("https://www.linkedin.com/oauth/v2/authorization")

import sysprint("\n🚀 OPEN THIS URL in your browser:")

import webbrowserprint(auth_url)

from urllib.parse import urlencode, parse_qs, urlparsewebbrowser.open(auth_url)



import requests# After login, LinkedIn redirects to your callback URL

redirect_response = input("\nPaste the FULL redirect URL here:\n")

# Load .env file if it exists (for local development)code = redirect_response.split("code=")[1].split("&")[0]

try:

    from dotenv import load_dotenv# Exchange code for token

    load_dotenv()token = oauth.fetch_token(

    print("✓ Loaded .env file")    "https://www.linkedin.com/oauth/v2/accessToken",

except ImportError:    client_secret=client_secret,

    print("⚠ python-dotenv not installed. Install with: pip install python-dotenv")    code=code,

    print("  (Optional - you can also export env vars manually)"))



# Configuration from environmentprint("\n✅ ACCESS TOKEN (store as LINKEDIN_ACCESS_TOKEN):")

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")print(token["access_token"])

LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")if "refresh_token" in token:

REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:3000/auth/linkedin/callback")    print("\n♻️ REFRESH TOKEN (store as LINKEDIN_REFRESH_TOKEN):")

LINKEDIN_SCOPES = os.getenv("LINKEDIN_SCOPES", "w_organization_social r_liteprofile w_member_social")    print(token["refresh_token"])


# Validate required variables
assert LINKEDIN_CLIENT_ID, "❌ LINKEDIN_CLIENT_ID not set in environment"
assert LINKEDIN_CLIENT_SECRET, "❌ LINKEDIN_CLIENT_SECRET not set in environment"

print(f"\n✓ Client ID: {LINKEDIN_CLIENT_ID}")
print(f"✓ Redirect URI: {REDIRECT_URI}")
print(f"✓ Scopes: {LINKEDIN_SCOPES}")


def get_authorization_url():
    """Build the LinkedIn OAuth authorization URL."""
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": LINKEDIN_SCOPES,
    }
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    return f"{base_url}?{urlencode(params)}"


def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token."""
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error exchanging code for token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)


def get_user_profile(access_token):
    """Get LinkedIn user profile to display authenticated user."""
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(
            "https://api.linkedin.com/v2/me",
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        profile = response.json()
        return profile.get("localizedFirstName", ""), profile.get("localizedLastName", "")
    except:
        return None, None


def main():
    print("\n" + "="*70)
    print("  LinkedIn OAuth 2.0 Token Generator")
    print("="*70)
    
    # Step 1: Get authorization URL
    auth_url = get_authorization_url()
    print("\n📋 Step 1: Authorize the application")
    print(f"\nOpening browser to:\n{auth_url}\n")
    
    # Try to open browser automatically
    try:
        webbrowser.open(auth_url)
        print("✓ Browser opened automatically")
    except:
        print("⚠ Could not open browser. Please copy the URL above manually.")
    
    print("\n" + "-"*70)
    print("After authorizing, you'll be redirected to:")
    print(f"{REDIRECT_URI}?code=XXXXX&state=XXXXX")
    print("\nThe page may show an error (that's OK if localhost isn't running).")
    print("Just copy the 'code' parameter from the URL.")
    print("-"*70)
    
    # Step 2: Get authorization code from user
    print("\n📋 Step 2: Enter the authorization code")
    auth_code = input("\nPaste the 'code' parameter here: ").strip()
    
    if not auth_code:
        print("❌ No code provided. Exiting.")
        sys.exit(1)
    
    # Step 3: Exchange code for token
    print("\n📋 Step 3: Exchanging code for access token...")
    token_data = exchange_code_for_token(auth_code)
    
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", "unknown")
    refresh_token = token_data.get("refresh_token")
    
    if not access_token:
        print("❌ Failed to get access token")
        print(f"Response: {token_data}")
        sys.exit(1)
    
    print("\n✅ Success! Access token generated.")
    
    # Step 4: Get user profile (optional, for verification)
    first_name, last_name = get_user_profile(access_token)
    if first_name:
        print(f"\n👤 Authenticated as: {first_name} {last_name}")
    
    # Step 5: Display results
    print("\n" + "="*70)
    print("  🎉 Your LinkedIn API Credentials")
    print("="*70)
    
    print(f"\n📝 Access Token (expires in {expires_in} seconds):")
    print(f"\n{access_token}\n")
    
    if refresh_token:
        print(f"🔄 Refresh Token:")
        print(f"\n{refresh_token}\n")
    else:
        print("ℹ️  No refresh token provided (tokens expire in ~60 days)")
    
    print("\n" + "="*70)
    print("  📋 Next Steps")
    print("="*70)
    
    print("\n1. Add to GitHub Secrets (Settings → Secrets → Actions):")
    print(f"\n   LINKEDIN_ACCESS_TOKEN = {access_token[:20]}...")
    
    print("\n2. (Optional) Add to your .env file for local testing:")
    print(f"\n   LINKEDIN_ACCESS_TOKEN={access_token}")
    if refresh_token:
        print(f"   LINKEDIN_REFRESH_TOKEN={refresh_token}")
    
    print("\n3. Get your organization ID:")
    print("\n   • Go to your LinkedIn Company Page")
    print("   • Click 'About' → Look for Company ID in URL")
    print("   • Or use: https://www.linkedin.com/company/YOUR_COMPANY")
    print("   • Extract the number/ID and add to secrets:")
    print("\n   LINKEDIN_ORG_ID = <your_org_id>")
    
    print("\n4. Test posting:")
    print("\n   python main.py --platform linkedin")
    
    print("\n" + "="*70)
    print(f"\n⚠️  Token expires in {expires_in} seconds (~{int(expires_in)//86400} days)")
    print("   You'll need to regenerate it when it expires.")
    print("\n✓ Done! Your LinkedIn integration is ready.\n")


if __name__ == "__main__":
    main()
