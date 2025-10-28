import os
import sys
import time
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import io

import tweepy
import requests
from notion_client import Client

# ----- Config -----
UTC_NOW = datetime.now(timezone.utc)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

# X (Twitter) credentials
X_API_KEY = os.getenv("X_API_KEY") or os.getenv("API_KEY")
X_API_SECRET = os.getenv("X_API_SECRET") or os.getenv("API_KEY_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET") or os.getenv("ACCESS_TOKEN_SECRET")

# LinkedIn credentials
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORG_ID = os.getenv("LINKEDIN_ORG_ID", "")  # Optional: use user posts if not set

# ----- Logging -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ----- Clients -----
notion = Client(auth=NOTION_TOKEN)

# ----- Helpers -----
def iso(dt_obj: datetime) -> str:
    """Convert datetime to ISO 8601 string with 'Z' suffix (UTC)."""
    return dt_obj.replace(microsecond=0).isoformat().replace('+00:00', 'Z')

def notion_query_scheduled(db_id: str) -> List[Dict[str, Any]]:
    """
    Fetch pages where Status = Scheduled and Scheduled Time <= now (UTC).
    """
    return notion.databases.query(
        database_id=db_id,
        filter={
            "and": [
                {"property": "Status", "select": {"equals": "Scheduled"}},
                {"property": "Scheduled Time", "date": {"before": iso(UTC_NOW)}},
            ]
        },
        sorts=[{"property": "Scheduled Time", "direction": "ascending"}],
    )["results"]

def get_prop_text(p: Dict[str, Any], name: str) -> str:
    val = p["properties"].get(name)
    if not val:
        return ""
    # Title or Rich text
    blocks = val.get("title") or val.get("rich_text") or []
    return "".join(chunk.get("plain_text", "") for chunk in blocks)

def get_prop_number(p: Dict[str, Any], name: str) -> int:
    v = p["properties"].get(name, {}).get("number")
    return int(v) if v is not None else 0

def get_media_urls(p: Dict[str, Any]) -> List[str]:
    txt = get_prop_text(p, "Media URLs")
    urls = [u.strip() for u in txt.split() if u.strip().startswith("http")]
    return urls

def update_notion_status(page_id: str, status: str, platform: str = None, 
                        post_url: str = None, error_msg: str = None):
    """Update Notion page with status and optional post URL."""
    properties = {
        "Status": {"select": {"name": status}},
    }
    
    if status == "Posted":
        properties["Posted Time"] = {"date": {"start": iso(UTC_NOW)}}
    
    if post_url and platform:
        if platform == "x":
            properties["Tweet URL"] = {"url": post_url}
        elif platform == "linkedin":
            properties["LinkedIn URL"] = {"url": post_url}
    
    if error_msg:
        properties["Error Message"] = {"rich_text": [{"text": {"content": error_msg[:1800]}}]}
    else:
        properties["Error Message"] = {"rich_text": []}
    
    notion.pages.update(page_id, properties=properties)

# ----- X (Twitter) Posting -----
def post_to_x(text: str, media_urls: List[str] = None) -> str:
    """
    Post to X (Twitter) and return the tweet URL.
    """
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        raise RuntimeError("Missing X API credentials")
    
    # Create Twitter client
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET
    )
    
    media_ids = []
    
    # Upload media if provided (requires API v1.1)
    if media_urls:
        auth = tweepy.OAuth1UserHandler(
            X_API_KEY, X_API_SECRET,
            X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
        )
        api = tweepy.API(auth)
        
        for media_url in media_urls[:4]:  # Twitter allows max 4 images
            try:
                logger.info(f"Downloading media from {media_url}")
                response = requests.get(media_url, timeout=10)
                response.raise_for_status()
                
                # Upload to Twitter
                media = api.media_upload(filename="temp.jpg", file=io.BytesIO(response.content))
                media_ids.append(media.media_id)
                logger.info(f"Uploaded media: {media.media_id}")
            except Exception as e:
                logger.warning(f"Failed to upload media {media_url}: {e}")
    
    # Post tweet
    response = client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
    tweet_id = response.data['id']
    
    # Get username for URL (use a default or fetch from API)
    # For simplicity, we'll construct URL with generic path
    tweet_url = f"https://x.com/i/web/status/{tweet_id}"
    
    logger.info(f"Posted to X: {tweet_url}")
    return tweet_url

# ----- LinkedIn Posting -----
def post_to_linkedin(text: str, media_urls: List[str] = None) -> str:
    """
    Post to LinkedIn and return the post URL.
    Supports both user posts and organization posts.
    """
    if not LINKEDIN_ACCESS_TOKEN:
        raise RuntimeError("Missing LinkedIn access token")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # Determine author (organization or user)
    if LINKEDIN_ORG_ID:
        author = f"urn:li:organization:{LINKEDIN_ORG_ID}"
    else:
        # Get user's profile to get their URN
        try:
            profile_response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers=headers,
                timeout=10
            )
            profile_response.raise_for_status()
            user_id = profile_response.json().get("id")
            author = f"urn:li:person:{user_id}"
        except Exception as e:
            logger.error(f"Failed to get LinkedIn user profile: {e}")
            raise RuntimeError("Could not determine LinkedIn author URN")
    
    # Build post payload
    payload = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    
    # If media URLs provided, upload and attach (simplified - LinkedIn media upload is complex)
    # For now, we'll just post text. Full media support requires multi-step upload process
    if media_urls:
        logger.warning("LinkedIn media upload not fully implemented yet - posting text only")
    
    # Post to LinkedIn
    try:
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        
        # Extract post ID from response
        post_data = response.json()
        post_id = post_data.get("id", "")
        
        # Convert URN to URL
        # URN format: urn:li:share:1234567890
        # URL format: https://www.linkedin.com/feed/update/urn:li:share:1234567890
        if post_id:
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"
        else:
            post_url = "https://www.linkedin.com/feed/"
        
        logger.info(f"Posted to LinkedIn: {post_url}")
        return post_url
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"LinkedIn API error: {e}")
        logger.error(f"Response: {e.response.text if e.response else 'No response'}")
        raise

# ----- Main Posting Logic -----
def run(platform: str):
    """
    Main posting function. Platform can be 'x' or 'linkedin'.
    """
    if platform not in ['x', 'linkedin']:
        raise ValueError(f"Invalid platform: {platform}. Must be 'x' or 'linkedin'")
    
    # Validate required credentials
    if platform == 'x':
        if not all([NOTION_TOKEN, NOTION_DB_ID, X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
            raise RuntimeError("Missing required X/Twitter credentials")
    elif platform == 'linkedin':
        if not all([NOTION_TOKEN, NOTION_DB_ID, LINKEDIN_ACCESS_TOKEN]):
            raise RuntimeError("Missing required LinkedIn credentials")
    
    logger.info(f"=== Starting {platform.upper()} Poster ===")
    
    # Query scheduled posts
    pages = notion_query_scheduled(NOTION_DB_ID)
    if not pages:
        logger.info(f"No scheduled posts due for {platform.upper()}.")
        return
    
    logger.info(f"Found {len(pages)} post(s) due for {platform.upper()}.")
    
    # Group by Thread Group ID (if present)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pages:
        group_id = get_prop_text(p, "Thread Group ID") or p["id"]
        groups.setdefault(group_id, []).append(p)
    
    for gid, items in groups.items():
        # Sort inside thread by Thread Position
        items.sort(key=lambda x: get_prop_number(x, "Thread Position") or 0)
        
        for page in items:
            page_id = page["id"]
            text = get_prop_text(page, "Tweet Content").strip()
            media_urls = get_media_urls(page)
            
            if not text:
                update_notion_status(page_id, "Failed", error_msg="Empty Tweet Content")
                continue
            
            try:
                # Post to platform
                if platform == 'x':
                    post_url = post_to_x(text, media_urls)
                elif platform == 'linkedin':
                    post_url = post_to_linkedin(text, media_urls)
                
                # Update Notion with success + URL
                update_notion_status(page_id, "Posted", platform=platform, post_url=post_url)
                logger.info(f"Successfully posted to {platform.upper()}: {page_id[:8]}...")
                
                # Rate limiting: polite pacing
                time.sleep(2)
            
            except tweepy.errors.Forbidden as e:
                error_msg = str(e)
                if "duplicate content" in error_msg.lower():
                    logger.warning(f"Duplicate content detected - marking as Failed")
                else:
                    logger.error(f"X API forbidden error: {error_msg}")
                update_notion_status(page_id, "Failed", error_msg=error_msg)
            
            except tweepy.errors.TweepyException as e:
                logger.error(f"X API error: {e}")
                update_notion_status(page_id, "Failed", error_msg=str(e))
            
            except requests.exceptions.RequestException as e:
                logger.error(f"LinkedIn API error: {e}")
                update_notion_status(page_id, "Failed", error_msg=str(e))
            
            except Exception as e:
                logger.exception("Unexpected error during posting")
                update_notion_status(page_id, "Failed", error_msg=str(e))
    
    logger.info(f"=== {platform.upper()} Poster Completed ===")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Post scheduled content to X or LinkedIn")
    parser.add_argument(
        "--platform",
        type=str,
        choices=["x", "linkedin"],
        required=True,
        help="Platform to post to: 'x' or 'linkedin'"
    )
    args = parser.parse_args()
    
    try:
        run(args.platform)
    except Exception as e:
        logger.exception(f"Fatal error in {args.platform.upper()} poster")
        sys.exit(1)
