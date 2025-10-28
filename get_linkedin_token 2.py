# get_linkedin_token.py
from requests_oauthlib import OAuth2Session
import os, webbrowser

# Load from environment
client_id = os.getenv("LINKEDIN_CLIENT_ID")
client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
redirect_uri = "http://localhost:3000/auth/linkedin/callback"

# Scopes: company posts + profile + refresh
scopes = ["w_organization_social", "r_liteprofile", "offline_access"]

oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scopes)
auth_url, _ = oauth.authorization_url("https://www.linkedin.com/oauth/v2/authorization")
print("\n🚀 OPEN THIS URL in your browser:")
print(auth_url)
webbrowser.open(auth_url)

# After login, LinkedIn redirects to your callback URL
redirect_response = input("\nPaste the FULL redirect URL here:\n")
code = redirect_response.split("code=")[1].split("&")[0]

# Exchange code for token
token = oauth.fetch_token(
    "https://www.linkedin.com/oauth/v2/accessToken",
    client_secret=client_secret,
    code=code,
)

print("\n✅ ACCESS TOKEN (store as LINKEDIN_ACCESS_TOKEN):")
print(token["access_token"])
if "refresh_token" in token:
    print("\n♻️ REFRESH TOKEN (store as LINKEDIN_REFRESH_TOKEN):")
    print(token["refresh_token"])
