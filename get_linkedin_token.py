#!/usr/bin/env python3
"""
LinkedIn OAuth 2.0 Token Generator
Generates access tokens for LinkedIn API with organization posting permissions.

Usage:
    1. Add credentials to .env file
    2. Run: python get_linkedin_token.py
    3. Follow the authorization URL in your browser
    4. Paste the code from redirect URL
    5. Copy the access token to GitHub Secrets
"""

import os
import sys
import logging
import webbrowser
from urllib.parse import urlencode

import requests

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✓ Loaded .env file")
    print("✓ Loaded .env file")
except ImportError:
    logger.warning("⚠ python-dotenv not installed")
    print("⚠ python-dotenv not installed. Install with: pip install python-dotenv")
    print("  (Optional - you can also export env vars manually)")

# Configuration from environment
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:3000/auth/linkedin/callback")
LINKEDIN_SCOPES = os.getenv("LINKEDIN_SCOPES", "w_organization_social r_liteprofile w_member_social")

logger.debug(f"LinkedIn Client ID: {LINKEDIN_CLIENT_ID[:20] if LINKEDIN_CLIENT_ID else 'NOT SET'}...")
logger.debug(f"LinkedIn Client Secret: {LINKEDIN_CLIENT_SECRET[:20] if LINKEDIN_CLIENT_SECRET else 'NOT SET'}...")
logger.debug(f"Redirect URI: {REDIRECT_URI}")
logger.debug(f"LinkedIn Scopes: {LINKEDIN_SCOPES}")

# Validate required variables
if not LINKEDIN_CLIENT_ID:
    logger.error("❌ LINKEDIN_CLIENT_ID not set in environment")
    assert False, "❌ LINKEDIN_CLIENT_ID not set in environment"

if not LINKEDIN_CLIENT_SECRET:
    logger.error("❌ LINKEDIN_CLIENT_SECRET not set in environment")
    assert False, "❌ LINKEDIN_CLIENT_SECRET not set in environment"

logger.info(f"✓ Configuration loaded - Client ID: {LINKEDIN_CLIENT_ID[:20]}...")
print(f"\n✓ Client ID: {LINKEDIN_CLIENT_ID}")
print(f"✓ Redirect URI: {REDIRECT_URI}")
print(f"✓ Scopes: {LINKEDIN_SCOPES}")


def get_authorization_url():
    """Build the LinkedIn OAuth authorization URL."""
    logger.debug("get_authorization_url() called")
    
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": LINKEDIN_SCOPES,
    }
    
    logger.debug(f"OAuth parameters: {params}")
    
    base_url = "https://www.linkedin.com/oauth/v2/authorization"
    auth_url = f"{base_url}?{urlencode(params)}"
    
    logger.debug(f"Generated authorization URL: {auth_url}")
    logger.info(f"🔗 Authorization URL generated")
    
    return auth_url


def exchange_code_for_token(auth_code):
    """Exchange authorization code for access token."""
    logger.debug(f"exchange_code_for_token() called - Code length: {len(auth_code)}")
    logger.debug(f"Authorization code: {auth_code[:20]}...")
    
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
    }
    
    logger.debug(f"Token exchange request data: {dict(data, client_secret='***MASKED***')}")
    logger.info(f"🔄 Exchanging authorization code for access token...")
    
    try:
        logger.debug(f"POST {token_url}")
        response = requests.post(token_url, data=data, timeout=15)
        
        logger.debug(f"Token exchange response status: {response.status_code}")
        
        response.raise_for_status()
        
        token_data = response.json()
        logger.debug(f"Token response keys: {list(token_data.keys())}")
        
        if "access_token" in token_data:
            logger.info(f"✅ Successfully obtained access token")
            logger.debug(f"Access token: {token_data['access_token'][:20]}...")
            logger.debug(f"Token expires in: {token_data.get('expires_in', 'unknown')} seconds")
        else:
            logger.warning(f"⚠️ No access_token in response")
        
        return token_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Error exchanging code for token: {e}", exc_info=True)
        print(f"\n❌ Error exchanging code for token: {e}")
        
        if hasattr(e, 'response') and e.response:
            logger.error(f"Response status code: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            
            print(f"\n📋 Response status: {e.response.status_code}")
            print(f"📋 Response body: {e.response.text}")
            print(f"\n💡 This usually means:")
            print(f"   - Client Secret is incorrect")
            print(f"   - Client ID doesn't match the Client Secret")
            print(f"   - Authorization code expired (get a new one)")
        
        sys.exit(1)


def get_user_profile(access_token):
    """Get LinkedIn user profile to display authenticated user."""
    logger.debug("get_user_profile() called")
    logger.debug(f"Access token: {access_token[:20]}...")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    profile_url = "https://api.linkedin.com/v2/me"
    
    logger.info(f"👤 Fetching user profile...")
    
    try:
        logger.debug(f"GET {profile_url}")
        response = requests.get(profile_url, headers=headers, timeout=10)
        
        logger.debug(f"Profile API response status: {response.status_code}")
        
        response.raise_for_status()
        
        profile = response.json()
        logger.debug(f"Profile response keys: {list(profile.keys())}")
        
        first_name = profile.get("localizedFirstName", "")
        last_name = profile.get("localizedLastName", "")
        
        logger.info(f"✅ Profile retrieved: {first_name} {last_name}")
        logger.debug(f"First name: {first_name}, Last name: {last_name}")
        
        return first_name, last_name
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to get user profile: {e}")
        logger.debug("Profile fetch failed", exc_info=True)
        return None, None


def main():
    logger.info("🚀 Starting LinkedIn OAuth 2.0 Token Generator")
    
    print("\n" + "="*70)
    print("  LinkedIn OAuth 2.0 Token Generator")
    print("="*70)
    
    # Step 1: Get authorization URL
    logger.info("📋 Step 1: Building authorization URL")
    auth_url = get_authorization_url()
    
    print("\n📋 Step 1: Authorize the application")
    print(f"\nOpening browser to:\n{auth_url}\n")
    
    # Try to open browser automatically
    try:
        logger.debug("Attempting to open browser...")
        webbrowser.open(auth_url)
        logger.info("✅ Browser opened automatically")
        print("✓ Browser opened automatically")
    except Exception as e:
        logger.warning(f"⚠️ Could not open browser: {e}")
        print("⚠ Could not open browser. Please copy the URL above manually.")
    
    print("\n" + "-"*70)
    print("After authorizing, you'll be redirected to:")
    print(f"{REDIRECT_URI}?code=XXXXX&state=XXXXX")
    print("\nThe page may show an error (that's OK if localhost isn't running).")
    print("Just copy the 'code' parameter from the URL.")
    print("-"*70)
    
    # Step 2: Get authorization code from user
    logger.info("📋 Step 2: Waiting for authorization code from user")
    print("\n📋 Step 2: Enter the authorization code")
    auth_code = input("\nPaste the 'code' parameter here: ").strip()
    
    if not auth_code:
        logger.error("❌ No authorization code provided")
        print("❌ No code provided. Exiting.")
        sys.exit(1)
    
    logger.info(f"✅ Authorization code received (length: {len(auth_code)})")
    
    # Step 3: Exchange code for token
    logger.info("📋 Step 3: Exchanging authorization code for access token")
    print("\n📋 Step 3: Exchanging code for access token...")
    
    token_data = exchange_code_for_token(auth_code)
    
    access_token = token_data.get("access_token")
    expires_in = token_data.get("expires_in", "unknown")
    refresh_token = token_data.get("refresh_token")
    
    if not access_token:
        logger.critical("❌ Failed to get access token from response")
        logger.debug(f"Token response data: {token_data}")
        print("❌ Failed to get access token")
        print(f"Response: {token_data}")
        sys.exit(1)
    
    logger.info(f"✅ Access token obtained successfully (expires in {expires_in} seconds)")
    print("\n✅ Success! Access token generated.")
    
    # Step 4: Get user profile (optional, for verification)
    logger.info("📋 Step 4: Verifying token by fetching user profile")
    first_name, last_name = get_user_profile(access_token)
    
    if first_name:
        logger.info(f"✅ Token verified - User: {first_name} {last_name}")
        print(f"\n👤 Authenticated as: {first_name} {last_name}")
    else:
        logger.warning("⚠️ Could not verify token with profile fetch")
    
    # Step 5: Display results
    logger.info("📋 Step 5: Displaying credentials")
    print("\n" + "="*70)
    print("  🎉 Your LinkedIn API Credentials")
    print("="*70)
    
    print(f"\n📝 Access Token (expires in {expires_in} seconds):")
    print(f"\n{access_token}\n")
    
    if refresh_token:
        logger.info(f"✅ Refresh token also obtained")
        print(f"🔄 Refresh Token:")
        print(f"\n{refresh_token}\n")
    else:
        logger.info("ℹ️ No refresh token in response")
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
    
    logger.info("🎉 Token generation complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"❌ Fatal error in main(): {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
