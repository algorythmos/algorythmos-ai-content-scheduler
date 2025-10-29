#!/usr/bin/env python3
"""Quick test script to debug LinkedIn OAuth token exchange."""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

print("=" * 70)
print("LinkedIn OAuth Debug Test")
print("=" * 70)
print(f"Client ID: {CLIENT_ID}")
print(f"Client Secret: {CLIENT_SECRET[:10]}...{CLIENT_SECRET[-5:] if CLIENT_SECRET else 'None'}")
print(f"Redirect URI: {REDIRECT_URI}")
print("=" * 70)

# Get a fresh authorization code
auth_code = input("\nPaste the authorization code from the URL: ").strip()

# Extract just the code if full URL was pasted
if "code=" in auth_code:
    auth_code = auth_code.split("code=")[1].split("&")[0]

print(f"\nUsing code: {auth_code[:20]}...")

# Make the token exchange request
token_url = "https://www.linkedin.com/oauth/v2/accessToken"
data = {
    "grant_type": "authorization_code",
    "code": auth_code,
    "redirect_uri": REDIRECT_URI,
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
}

print(f"\n🔄 Making POST request to: {token_url}")
print(f"📦 Request data:")
for key, value in data.items():
    if key == "client_secret":
        print(f"   {key}: {value[:10]}...{value[-5:]}")
    elif key == "code":
        print(f"   {key}: {value[:20]}...")
    else:
        print(f"   {key}: {value}")

try:
    response = requests.post(token_url, data=data, timeout=15)
    
    print(f"\n✓ Response Status Code: {response.status_code}")
    print(f"✓ Response Headers: {dict(response.headers)}")
    print(f"\n📋 Response Body:")
    print(response.text)
    
    if response.status_code == 200:
        token_data = response.json()
        print(f"\n✅ SUCCESS! Access Token: {token_data.get('access_token', 'N/A')}")
    else:
        print(f"\n❌ ERROR: Status {response.status_code}")
        
except Exception as e:
    print(f"\n❌ Exception occurred: {e}")
    if hasattr(e, 'response'):
        print(f"Response: {e.response.text if e.response else 'None'}")
