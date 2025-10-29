import os
import sys
import time
import json
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import io

import tweepy
import requests
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
# Configure logging level from environment variable (default: INFO)
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)
logger.debug(f"Logging initialized at level: {log_level}")

# ----- Clients -----
try:
    notion = Client(auth=NOTION_TOKEN)
    logger.debug("Notion client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Notion client: {e}", exc_info=True)
    raise

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
                        post_url: str = None, error_msg: str = None, visibility_warning: str = None):
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
    
    # Combine error message and visibility warning
    full_error = []
    if error_msg:
        full_error.append(f"Error: {error_msg}")
    if visibility_warning:
        full_error.append(f"⚠️ Visibility: {visibility_warning}")
    
    if full_error:
        properties["Error Message"] = {"rich_text": [{"text": {"content": "\n".join(full_error)[:1800]}}]}
    else:
        properties["Error Message"] = {"rich_text": []}
    
    notion.pages.update(page_id, properties=properties)
    
    if visibility_warning:
        logger.warning(f"Updated Notion with visibility warning: {visibility_warning}")

# ----- Post Visibility Verification -----
def verify_x_post(tweet_id: str) -> Dict[str, Any]:
    """
    Verify that a tweet is actually visible and public.
    Returns dict with 'visible', 'status', and 'error' keys.
    """
    try:
        client = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN") or X_ACCESS_TOKEN)
        
        # Fetch tweet details
        tweet = client.get_tweet(
            id=tweet_id,
            tweet_fields=["created_at", "public_metrics", "possibly_sensitive"]
        )
        
        if tweet.data:
            logger.debug(f"✅ Tweet {tweet_id} is visible")
            logger.debug(f"Tweet data: {tweet.data}")
            return {
                "visible": True,
                "status": "PUBLISHED",
                "metrics": tweet.data.public_metrics,
                "error": None
            }
        else:
            logger.warning(f"⚠️ Tweet {tweet_id} exists but no data returned")
            return {
                "visible": False,
                "status": "UNKNOWN",
                "error": "No data in API response"
            }
    
    except tweepy.errors.NotFound:
        logger.error(f"❌ Tweet {tweet_id} not found - may be deleted or hidden")
        return {
            "visible": False,
            "status": "NOT_FOUND",
            "error": "Tweet not found (deleted or hidden)"
        }
    except Exception as e:
        logger.error(f"Error verifying tweet {tweet_id}: {e}", exc_info=True)
        return {
            "visible": False,
            "status": "ERROR",
            "error": str(e)
        }

def verify_linkedin_post(post_urn: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Verify that a LinkedIn post is actually visible and published.
    Retries if status is PROCESSING (LinkedIn moderation delay).
    Returns dict with 'visible', 'status', and 'error' keys.
    """
    if not LINKEDIN_ACCESS_TOKEN:
        return {"visible": False, "status": "ERROR", "error": "No access token"}
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    for attempt in range(max_retries):
        try:
            # Query post details
            response = requests.get(
                f"https://api.linkedin.com/v2/ugcPosts/{post_urn}",
                headers=headers,
                timeout=10
            )
            
            logger.debug(f"LinkedIn verify attempt {attempt + 1}/{max_retries}: status {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                lifecycle_state = data.get("lifecycleState", "UNKNOWN")
                visibility = data.get("visibility", {})
                
                logger.debug(f"LinkedIn post {post_urn}: lifecycleState={lifecycle_state}, visibility={visibility}")
                
                if lifecycle_state == "PUBLISHED":
                    logger.debug(f"✅ LinkedIn post {post_urn} is published")
                    return {
                        "visible": True,
                        "status": "PUBLISHED",
                        "lifecycle": lifecycle_state,
                        "visibility": visibility,
                        "error": None
                    }
                elif lifecycle_state == "PROCESSING":
                    logger.info(f"⏳ LinkedIn post {post_urn} still processing (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(60)  # Wait 60s before retry
                        continue
                    return {
                        "visible": False,
                        "status": "PROCESSING",
                        "error": f"Still processing after {max_retries * 60}s - check manually"
                    }
                else:
                    logger.warning(f"⚠️ LinkedIn post {post_urn} has unexpected state: {lifecycle_state}")
                    return {
                        "visible": False,
                        "status": lifecycle_state,
                        "error": f"Unexpected lifecycle state: {lifecycle_state}"
                    }
            
            elif response.status_code == 404:
                logger.error(f"❌ LinkedIn post {post_urn} not found")
                return {
                    "visible": False,
                    "status": "NOT_FOUND",
                    "error": "Post not found (may be deleted or hidden)"
                }
            else:
                logger.error(f"LinkedIn verify API error: {response.status_code} - {response.text}")
                return {
                    "visible": False,
                    "status": "ERROR",
                    "error": f"API error {response.status_code}: {response.text[:200]}"
                }
        
        except Exception as e:
            logger.error(f"Error verifying LinkedIn post {post_urn}: {e}", exc_info=True)
            if attempt < max_retries - 1:
                time.sleep(60)
                continue
            return {
                "visible": False,
                "status": "ERROR",
                "error": str(e)
            }
    
    return {
        "visible": False,
        "status": "TIMEOUT",
        "error": f"Verification timed out after {max_retries} attempts"
    }

# ----- X (Twitter) Posting -----
def post_to_x(text: str, media_urls: List[str] = None) -> str:
    """
    Post to X (Twitter) and return the tweet URL.
    """
    logger.debug(f"post_to_x() called - Text length: {len(text)}, Media URLs: {len(media_urls) if media_urls else 0}")
    
    if not all([X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        logger.error("Missing X API credentials")
        raise RuntimeError("Missing X API credentials")
    
    logger.debug("X API credentials verified")
    
    # Create Twitter client
    try:
        client = tweepy.Client(
            consumer_key=X_API_KEY,
            consumer_secret=X_API_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET
        )
        logger.debug("Tweepy client created successfully")
    except Exception as e:
        logger.error(f"Failed to create Tweepy client: {e}", exc_info=True)
        raise
    
    media_ids = []
    
    # Upload media if provided (requires API v1.1)
    if media_urls:
        logger.info(f"Uploading {len(media_urls)} media files to X")
        auth = tweepy.OAuth1UserHandler(
            X_API_KEY, X_API_SECRET,
            X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
        )
        api = tweepy.API(auth)
        
        for i, media_url in enumerate(media_urls[:4], 1):  # Twitter allows max 4 images
            try:
                logger.debug(f"Downloading media {i}/{len(media_urls[:4])} from {media_url}")
                response = requests.get(media_url, timeout=10)
                response.raise_for_status()
                logger.debug(f"Downloaded {len(response.content)} bytes")
                
                # Upload to Twitter
                logger.debug(f"Uploading media to X API")
                media = api.media_upload(filename="temp.jpg", file=io.BytesIO(response.content))
                media_ids.append(media.media_id)
                logger.info(f"✅ Uploaded media {i}: ID {media.media_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to upload media {media_url}: {type(e).__name__}: {e}", exc_info=True)
    
    # Post tweet
    logger.info(f"🐦 Posting tweet to X (text length: {len(text)}, media count: {len(media_ids)})")
    logger.debug(f"Tweet text: {text}")
    
    try:
        response = client.create_tweet(text=text, media_ids=media_ids if media_ids else None)
        tweet_id = response.data['id']
        logger.debug(f"X API response: {response}")
        
        # Get username for URL (use a default or fetch from API)
        # For simplicity, we'll construct URL with generic path
        tweet_url = f"https://x.com/i/web/status/{tweet_id}"
        
        logger.info(f"✅ Posted to X successfully: {tweet_url}")
        
        # Add human-like delay before verification
        time.sleep(5)
        
        # Verify post visibility
        logger.info(f"🔍 Verifying tweet visibility...")
        verification = verify_x_post(tweet_id)
        
        if not verification["visible"]:
            logger.error(f"❌ Tweet created but NOT VISIBLE: {verification['error']}")
            logger.error(f"   Status: {verification['status']}")
            logger.error(f"   Tweet ID: {tweet_id}")
            logger.error(f"   This may indicate:")
            logger.error(f"   - Account flagged for automation (follow 20+ accounts to warm up)")
            logger.error(f"   - Tweet hidden by X algorithm (low engagement/new account)")
            logger.error(f"   - Content moderation (check X rules)")
            # Still return URL so it's tracked in Notion
        else:
            logger.info(f"✅ Tweet verified as visible with metrics: {verification.get('metrics')}")
        
        return tweet_url
    except Exception as e:
        logger.error(f"❌ Failed to post to X: {type(e).__name__}: {e}", exc_info=True)
        raise

# ----- LinkedIn Posting -----
def post_to_linkedin(text: str, media_urls: List[str] = None) -> str:
    """
    Post to LinkedIn and return the post URL.
    Supports both user posts and organization posts.
    """
    logger.debug(f"post_to_linkedin() called - Text length: {len(text)}, Media URLs: {len(media_urls) if media_urls else 0}")
    
    if not LINKEDIN_ACCESS_TOKEN:
        logger.error("Missing LinkedIn access token")
        raise RuntimeError("Missing LinkedIn access token")
    
    logger.debug("LinkedIn access token verified")
    
    headers = {
        "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN[:20]}...",  # Log only first 20 chars
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0"
    }
    
    # Determine author (organization or user)
    if LINKEDIN_ORG_ID:
        author = f"urn:li:organization:{LINKEDIN_ORG_ID}"
        logger.debug(f"Using organization author: {author}")
    else:
        # Get user's profile to get their URN
        logger.debug("Fetching LinkedIn user profile to get author URN")
        try:
            profile_response = requests.get(
                "https://api.linkedin.com/v2/me",
                headers={**headers, "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"},  # Use full token for actual request
                timeout=10
            )
            logger.debug(f"LinkedIn profile API response status: {profile_response.status_code}")
            profile_response.raise_for_status()
            
            user_data = profile_response.json()
            user_id = user_data.get("id")
            logger.debug(f"LinkedIn profile response: {json.dumps(user_data, indent=2)}")
            
            if not user_id:
                logger.error("LinkedIn profile response missing 'id' field")
                raise RuntimeError("Could not get user ID from LinkedIn profile")
            
            author = f"urn:li:person:{user_id}"
            logger.debug(f"Using user author: {author}")
        except Exception as e:
            logger.error(f"Failed to get LinkedIn user profile: {type(e).__name__}: {e}", exc_info=True)
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
    
    logger.debug(f"LinkedIn post payload: {json.dumps(payload, indent=2)}")
    
    # If media URLs provided, upload and attach (simplified - LinkedIn media upload is complex)
    # For now, we'll just post text. Full media support requires multi-step upload process
    if media_urls:
        logger.warning("⚠️ LinkedIn media upload not fully implemented yet - posting text only")
    
    # Post to LinkedIn
    logger.info(f"💼 Posting to LinkedIn (text length: {len(text)})")
    logger.debug(f"LinkedIn text: {text}")
    
    try:
        response = requests.post(
            "https://api.linkedin.com/v2/ugcPosts",
            headers={**headers, "Authorization": f"Bearer {LINKEDIN_ACCESS_TOKEN}"},  # Use full token
            json=payload,
            timeout=15
        )
        
        logger.debug(f"LinkedIn API response status: {response.status_code}")
        logger.debug(f"LinkedIn API response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        
        # Extract post ID from response
        post_data = response.json()
        logger.debug(f"LinkedIn post response: {json.dumps(post_data, indent=2)}")
        
        post_id = post_data.get("id", "")
        
        # Convert URN to URL
        # URN format: urn:li:share:1234567890
        # URL format: https://www.linkedin.com/feed/update/urn:li:share:1234567890
        if post_id:
            post_url = f"https://www.linkedin.com/feed/update/{post_id}"
            logger.info(f"✅ Posted to LinkedIn successfully: {post_url}")
            
            # Verify post visibility (with retry for PROCESSING state)
            logger.info(f"🔍 Verifying LinkedIn post visibility (may take up to 3 min)...")
            verification = verify_linkedin_post(post_id, max_retries=3)
            
            if not verification["visible"]:
                logger.error(f"❌ LinkedIn post created but NOT VISIBLE: {verification['error']}")
                logger.error(f"   Status: {verification['status']}")
                logger.error(f"   Post ID: {post_id}")
                logger.error(f"   This may indicate:")
                logger.error(f"   - Post still processing (check in 10-30 min)")
                logger.error(f"   - Content moderation review")
                logger.error(f"   - Organization admin approval required")
                logger.error(f"   - Visibility set to non-PUBLIC")
                logger.error(f"   Manual check: {post_url}")
            else:
                logger.info(f"✅ LinkedIn post verified as visible")
                logger.info(f"   Lifecycle: {verification.get('lifecycle')}")
                logger.info(f"   Visibility: {verification.get('visibility')}")
        else:
            post_url = "https://www.linkedin.com/feed/"
            logger.warning("⚠️ LinkedIn post created but no ID returned - using generic feed URL")
        
        return post_url
    
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ LinkedIn API HTTP error: {e}")
        if e.response:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to post to LinkedIn: {type(e).__name__}: {e}", exc_info=True)
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
            
            # Get platform-specific text
            # For X: Use X Text property (≤280 chars), fallback to Title
            # For LinkedIn: Use LinkedIn Text property, fallback to Title
            if platform == 'x':
                x_text = get_prop_text(page, "X Text").strip()
                if x_text:
                    text = x_text
                    logger.debug(f"Using X Text property: {len(text)} chars")
                else:
                    text = get_prop_text(page, "Title").strip()
                    logger.debug(f"X Text empty, using Title as fallback: {len(text)} chars")
            elif platform == 'linkedin':
                # Try LinkedIn Text property first
                linkedin_text = get_prop_text(page, "LinkedIn Text").strip()
                if linkedin_text:
                    text = linkedin_text
                    logger.debug(f"Using LinkedIn Text property: {len(text)} chars")
                else:
                    # Fallback to Title if LinkedIn Text is empty
                    text = get_prop_text(page, "Title").strip()
                    logger.debug(f"LinkedIn Text empty, using Title as fallback: {len(text)} chars")
            
            media_urls = get_media_urls(page)
            
            if not text:
                logger.warning(f"⚠️ Empty text for page {page_id[:8]}...")
                update_notion_status(page_id, "Failed", error_msg=f"Empty text for {platform}")
                continue
            
            # Validate character limits
            if platform == 'x' and len(text) > 280:
                logger.warning(f"⚠️ X text exceeds 280 chars ({len(text)}), truncating...")
                text = text[:277] + "..."
            elif platform == 'linkedin' and len(text) > 3000:
                logger.warning(f"⚠️ LinkedIn text exceeds 3000 chars ({len(text)}), truncating...")
                text = text[:2997] + "..."
            
            logger.info(f"📝 Posting to {platform.upper()} - Text length: {len(text)} chars")
            
            try:
                # Post to platform
                if platform == 'x':
                    post_url = post_to_x(text, media_urls)
                elif platform == 'linkedin':
                    post_url = post_to_linkedin(text, media_urls)
                
                # Update Notion with success + URL
                update_notion_status(page_id, "Posted", platform=platform, post_url=post_url)
                logger.info(f"✅ Successfully posted to {platform.upper()}: {page_id[:8]}...")
                
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
