#!/usr/bin/env python3
"""
AI Content Fetcher
Reads trusted AI RSS feeds, scores items, picks top 1, summarizes to ≤220 chars,
and creates a Notion row with Status=Scheduled for automated posting.
"""

import os
import sys
import json
import logging
import argparse
import time
import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from urllib.parse import urlparse
from collections import Counter

import feedparser
import tldextract
import requests
from dateutil import parser as date_parser
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Optional OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ----- Config -----
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

RSS_FEEDS = [
    "https://openai.com/blog/rss.xml",
    "https://blog.google/technology/ai/rss/",  # Google AI Blog
    "https://www.deepmind.com/blog/rss.xml",  # DeepMind
    "https://developer.nvidia.com/blog/feed/",
    "https://aws.amazon.com/blogs/machine-learning/feed/",  # AWS ML Blog
    "https://techcrunch.com/tag/artificial-intelligence/feed/",
    "https://venturebeat.com/category/ai/feed/",
]

BOOST_KEYWORDS = [
    "AI", "GenAI", "LLM", "agents", "model", "inference",
    "NVIDIA", "OpenAI", "Anthropic", "Meta"
]

MAX_ARTICLE_AGE_HOURS = 48
RECENCY_BOOST_HOURS = 24

# Platform-specific character limits
MAX_X_CHARS = 280  # X (Twitter) character limit
MAX_LINKEDIN_CHARS = 2000  # LinkedIn optimal limit (3000 max, 2000 best for engagement)
SUMMARY_MAX_CHARS = 220  # Legacy fallback summary length

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

# ----- Data Models -----
class NewsItem:
    def __init__(
        self,
        title: str,
        link: str,
        published: datetime,
        source_domain: str,
        image_url: Optional[str] = None,
        summary: Optional[str] = None
    ):
        self.title = title
        self.link = link
        self.published = published
        self.source_domain = source_domain
        self.image_url = image_url
        self.summary = summary
        self.score = 0.0

    def __repr__(self):
        return f"<NewsItem '{self.title[:50]}...' from {self.source_domain} score={self.score:.2f}>"


# ----- RSS Parsing -----
def get_recent_notion_content(notion: Client, db_id: str, days: int = 7) -> Set[Tuple[str, str]]:
    """
    Query Notion for recent Posted/Scheduled/Failed entries to prevent duplicates.
    Returns set of (normalized_title, link) tuples.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        # Query for entries from last N days
        results = notion.databases.query(
            database_id=db_id,
            filter={
                "or": [
                    {"property": "Status", "select": {"equals": "Posted"}},
                    {"property": "Status", "select": {"equals": "Scheduled"}},
                    {"property": "Status", "select": {"equals": "Failed"}},
                ],
                "and": [
                    {"property": "Scheduled Time", "date": {"after": cutoff_iso}}
                ]
            },
            page_size=100
        )
        
        seen_content = set()
        for page in results.get("results", []):
            # Extract title from Title property
            title_prop = page["properties"].get("Title", {})
            title_blocks = title_prop.get("title", [])
            if title_blocks:
                content = "".join(b.get("plain_text", "") for b in title_blocks)
                # Normalize: lowercase, strip, remove extra spaces
                normalized = " ".join(content.lower().strip().split())
                if normalized and not normalized.startswith("[error]"):
                    seen_content.add((normalized, ""))  # We only have content, not original link
        
        logger.info(f"Found {len(seen_content)} recent entries in Notion (last {days} days)")
        return seen_content
    
    except Exception as e:
        logger.warning(f"Failed to query recent Notion content: {e}")
        return set()


def normalize_title(title: str) -> str:
    """Normalize title for comparison."""
    return " ".join(title.lower().strip().split())


def title_similarity(title1: str, title2: str) -> float:
    """Calculate simple word overlap similarity between titles."""
    words1 = set(normalize_title(title1).split())
    words2 = set(normalize_title(title2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    
    return len(intersection) / len(union) if union else 0.0


def parse_feeds() -> List[NewsItem]:
    """
    Fetch and parse all RSS feeds, returning normalized NewsItem objects.
    Enhanced with:
    - Notion duplicate checking
    - Exponential backoff retries
    - Better deduplication
    """
    items = []
    seen = set()  # dedupe by (link, normalized_title)
    
    # Get recent Notion content to prevent duplicates
    notion_seen = set()
    if NOTION_TOKEN and NOTION_DB_ID:
        try:
            notion = Client(auth=NOTION_TOKEN)
            notion_seen = get_recent_notion_content(notion, NOTION_DB_ID, days=7)
        except Exception as e:
            logger.warning(f"Could not fetch Notion history: {e}")
    
    for feed_url in RSS_FEEDS:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching feed: {feed_url} (attempt {attempt + 1}/{max_retries})")
                response = requests.get(feed_url, timeout=15)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                
                if feed.bozo and not feed.entries:
                    logger.warning(f"Feed parsing issue for {feed_url}: {feed.bozo_exception}")
                    break  # Don't retry on parse errors
                
                for entry in feed.entries:
                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()
                    
                    if not title or not link:
                        continue
                    
                    # Normalize title for comparison
                    norm_title = normalize_title(title)
                    
                    # Dedupe by link and normalized title
                    dedupe_key = (link, norm_title)
                    if dedupe_key in seen:
                        continue
                    
                    # Check against recent Notion content
                    if any(title_similarity(norm_title, n[0]) > 0.7 for n in notion_seen):
                        logger.warning(f"Skipping duplicate from Notion history: {title[:60]}...")
                        continue
                    
                    seen.add(dedupe_key)
                    
                    # Parse published date
                    published_str = entry.get("published") or entry.get("updated")
                    if published_str:
                        try:
                            published = date_parser.parse(published_str)
                            # Make timezone-aware if naive
                            if published.tzinfo is None:
                                published = published.replace(tzinfo=timezone.utc)
                        except Exception:
                            published = datetime.now(timezone.utc)
                    else:
                        published = datetime.now(timezone.utc)
                    
                    # Extract domain
                    extracted = tldextract.extract(link)
                    source_domain = f"{extracted.domain}.{extracted.suffix}" if extracted.domain else "unknown"
                    
                    # Image URL (optional)
                    image_url = None
                    if "media_content" in entry and entry.media_content:
                        image_url = entry.media_content[0].get("url")
                    elif "media_thumbnail" in entry and entry.media_thumbnail:
                        image_url = entry.media_thumbnail[0].get("url")
                    elif "enclosures" in entry and entry.enclosures:
                        for enc in entry.enclosures:
                            if enc.get("type", "").startswith("image"):
                                image_url = enc.get("href")
                                break
                    
                    # Summary (for fallback)
                    summary = entry.get("summary", "")
                    
                    items.append(NewsItem(
                        title=title,
                        link=link,
                        published=published,
                        source_domain=source_domain,
                        image_url=image_url,
                        summary=summary
                    ))
                
                # Success - break retry loop
                break
                
            except requests.RequestException as e:
                logger.warning(f"Request error for {feed_url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    sleep_time = 5 * (2 ** attempt)  # Exponential backoff: 5s, 10s, 20s
                    logger.info(f"Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to fetch {feed_url} after {max_retries} attempts")
            except Exception as e:
                logger.error(f"Unexpected error fetching feed {feed_url}: {e}")
                break  # Don't retry on unexpected errors
    
    logger.info(f"Parsed {len(items)} unique items from {len(RSS_FEEDS)} feeds")
    return items


# ----- Scoring -----
def score_items(items: List[NewsItem], notion_recent: Optional[Set[Tuple[str, str]]] = None) -> List[NewsItem]:
    """
    Score items based on recency, keyword matches, and source diversity.
    Enhanced with:
    - Source diversity penalties (prevent over-representation)
    - Stricter recency boost (<24h heavily favored)
    - Similarity check against recent Notion content
    Filter out items older than 48h.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_ARTICLE_AGE_HOURS)
    recent_boost_cutoff = now - timedelta(hours=RECENCY_BOOST_HOURS)
    
    # Count source distribution
    source_counter = Counter(item.source_domain for item in items)
    total_items = len(items)
    
    filtered_items = []
    
    for item in items:
        # Filter out old items
        if item.published < cutoff:
            continue
        
        score = 0.0
        
        # Enhanced recency boost with stricter penalties
        if item.published:
            age_h = (now - item.published).total_seconds() / 3600
            if 0 <= age_h <= 6:
                score += 15  # Super fresh (< 6h)
            elif age_h <= 12:
                score += 12  # Very fresh (6-12h)
            elif age_h <= 24:
                score += 8   # Fresh (12-24h)
            elif age_h <= 36:
                score += 3   # Recent (24-36h)
            elif age_h <= 48:
                score += 1   # Older (36-48h) - minimal boost
            else:
                score -= 100  # Too old
        
        # Keyword matching: +2 per keyword in title
        title_upper = item.title.upper()
        for keyword in BOOST_KEYWORDS:
            if keyword.upper() in title_upper:
                score += 2.0
        
        # Source diversity penalty: penalize over-represented sources
        source_freq = source_counter[item.source_domain] / total_items
        if source_freq > 0.5:  # If source has >50% of items
            penalty = (source_freq - 0.5) * 10  # Penalty scales with over-representation
            score -= penalty
            logger.debug(f"Applied diversity penalty -{penalty:.2f} to {item.source_domain}")
        elif source_freq > 0.3:  # Moderate over-representation
            penalty = (source_freq - 0.3) * 5
            score -= penalty
        
        # Check similarity with recent Notion content if provided
        if notion_recent:
            norm_title = normalize_title(item.title)
            for notion_title, _ in notion_recent:
                similarity = title_similarity(norm_title, notion_title)
                if similarity > 0.6:  # High similarity threshold
                    penalty = (similarity - 0.6) * 15  # Strong penalty for similar content
                    score -= penalty
                    logger.debug(f"Applied similarity penalty -{penalty:.2f} for '{item.title[:40]}...'")
                    break
        
        item.score = score
        filtered_items.append(item)
    
    # Sort by score descending
    filtered_items.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"Scored and filtered to {len(filtered_items)} items (within {MAX_ARTICLE_AGE_HOURS}h)")
    
    # Log top 5 for debugging
    if filtered_items:
        logger.info("Top 5 scored items:")
        for i, item in enumerate(filtered_items[:5], 1):
            age_h = (now - item.published).total_seconds() / 3600
            logger.info(f"  {i}. [{item.score:.2f}] {item.title[:60]}... ({item.source_domain}, {age_h:.1f}h old)")
    
    return filtered_items


# ----- Summarization -----
def summarize_with_openai_dual(title: str, link: str, domain: str) -> Dict[str, Any]:
    """
    Use OpenAI to generate platform-specific summaries for X and LinkedIn.
    Returns dict with: {"x_text": str, "linkedin_text": str, "char_counts": dict}
    """
    logger.debug(f"summarize_with_openai_dual() called for: {title[:50]}...")
    
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        logger.error("OpenAI not available or API key missing")
        raise RuntimeError("OpenAI not available")
    
    # Initialize client
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.debug(f"OpenAI client initialized with model: {OPENAI_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
        raise
    
    # Enhanced prompt for dual-platform content generation
    sys_msg = """You are an expert AI content curator for Algorythmos, a France-based AI automation firm. Summarize the following article for social posting. Generate TWO versions:

1. **X (Twitter) Version**: ≤280 characters total (including spaces, emojis, hashtags). Make it punchy, engaging, with a hook, 1-2 key insights, a question or CTA, and end with the link. Use 1-2 relevant hashtags (#AI, #MachineLearning). Keep it concise and impactful.

2. **LinkedIn Version**: ≤2000 characters total. Professional tone for AI professionals: Start with a compelling hook, include 3-5 bullet takeaways, brief analysis/implications for enterprises, CTA to discuss or connect, and the link. Use 2-3 hashtags. Include emojis sparingly for readability. Make it informative and valuable.

Output STRICTLY as valid JSON (no extra text, no markdown code blocks):
{
  "x_text": "Full X post text here (≤280 chars)",
  "linkedin_text": "Full LinkedIn post text here (≤2000 chars)",
  "char_counts": {
    "x": [exact character count],
    "linkedin": [exact character count]
  }
}

Guidelines:
- Focus on AI innovation, business impact, and relevance to Algorythmos
- Be original—rephrase insights, don't just copy
- Ensure neutral, positive, professional tone
- If article details are limited, infer key points logically
- Do NOT include the URL in character counts (it will be appended separately)
- Keep X version under 280 chars, LinkedIn version under 2000 chars"""
    
    user_msg = f"""Article Details:
Title: {title}
Link: {link}
Source: {domain}

Generate engaging social media content for both X (Twitter) and LinkedIn."""
    
    logger.debug(f"Sending request to OpenAI - Model: {OPENAI_MODEL}")
    logger.debug(f"User message: {user_msg[:200]}...")
    
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,  # Higher temperature for more creative content
            max_tokens=1500,  # Increased for longer LinkedIn posts
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        logger.debug(f"OpenAI API response received - Usage: {resp.usage}")
        raw_response = (resp.choices[0].message.content or "").strip()
        logger.debug(f"Raw OpenAI response: {raw_response[:500]}...")
        
        # Parse JSON response
        try:
            result = json.loads(raw_response)
            logger.debug(f"Parsed JSON successfully - Keys: {list(result.keys())}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            logger.error(f"Raw response: {raw_response}")
            raise RuntimeError(f"Invalid JSON from OpenAI: {e}")
        
        # Extract and validate texts
        x_text = result.get("x_text", "").strip()
        linkedin_text = result.get("linkedin_text", "").strip()
        char_counts = result.get("char_counts", {})
        
        if not x_text or not linkedin_text:
            logger.error(f"Missing texts in OpenAI response: x_text={bool(x_text)}, linkedin_text={bool(linkedin_text)}")
            raise RuntimeError("OpenAI did not return both platform texts")
        
        # Validate and truncate if needed
        original_x_len = len(x_text)
        original_linkedin_len = len(linkedin_text)
        
        if len(x_text) > MAX_X_CHARS:
            logger.warning(f"⚠️ X text exceeded limit ({len(x_text)} > {MAX_X_CHARS}), truncating...")
            x_text = x_text[:MAX_X_CHARS - 3] + "..."
        
        if len(linkedin_text) > MAX_LINKEDIN_CHARS:
            logger.warning(f"⚠️ LinkedIn text exceeded limit ({len(linkedin_text)} > {MAX_LINKEDIN_CHARS}), truncating...")
            linkedin_text = linkedin_text[:MAX_LINKEDIN_CHARS - 3] + "..."
        
        logger.info(f"✅ Generated dual-platform content:")
        logger.info(f"   🐦 X: {len(x_text)}/{MAX_X_CHARS} chars (original: {original_x_len})")
        logger.info(f"   💼 LinkedIn: {len(linkedin_text)}/{MAX_LINKEDIN_CHARS} chars (original: {original_linkedin_len})")
        logger.debug(f"X text: {x_text}")
        logger.debug(f"LinkedIn text preview: {linkedin_text[:200]}...")
        
        return {
            "x_text": x_text,
            "linkedin_text": linkedin_text,
            "char_counts": {
                "x": len(x_text),
                "linkedin": len(linkedin_text)
            }
        }
    
    except Exception as e:
        logger.error(f"OpenAI API error: {type(e).__name__}: {e}", exc_info=True)
        raise


def summarize_fallback(item: NewsItem) -> Dict[str, Any]:
    """
    Fallback summarization when OpenAI is unavailable.
    Returns dict with x_text and linkedin_text.
    """
    logger.debug(f"summarize_fallback() called for: {item.title[:50]}...")
    import re
    
    # Start with title
    base_summary = item.title
    
    # Try to extract key content from summary
    if item.summary:
        clean_summary = re.sub(r'<[^>]+>', '', item.summary)
        clean_summary = re.sub(r'\s+', ' ', clean_summary).strip()
        
        sentences = clean_summary.split(". ")
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30:
                continue
            if any(kw.lower() in sentence.lower() for kw in BOOST_KEYWORDS):
                base_summary = sentence
                break
        else:
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) >= 30:
                    base_summary = sentence
                    break
    
    domain_suffix = f" ({item.source_domain})"
    
    # Generate X version (short)
    x_max_len = MAX_X_CHARS - len(domain_suffix) - len(" #AI ") - 30  # Reserve space for hashtag and link
    if len(base_summary) > x_max_len:
        x_text = base_summary[:x_max_len - 3] + "..."
    else:
        x_text = base_summary
    x_text = f"{x_text} #AI {domain_suffix}"
    
    # Generate LinkedIn version (longer, more detailed)
    linkedin_text = f"""📢 {item.title}

{base_summary}

This article from {item.source_domain} discusses important developments in AI and technology.

What are your thoughts on this development? 

#AI #Technology #Innovation
{domain_suffix}"""
    
    if len(linkedin_text) > MAX_LINKEDIN_CHARS:
        linkedin_text = linkedin_text[:MAX_LINKEDIN_CHARS - 3] + "..."
    
    logger.info(f"Generated fallback summaries: X={len(x_text)} chars, LinkedIn={len(linkedin_text)} chars")
    
    return {
        "x_text": x_text,
        "linkedin_text": linkedin_text,
        "char_counts": {
            "x": len(x_text),
            "linkedin": len(linkedin_text)
        }
    }


def summarize_item(item: NewsItem) -> Dict[str, Any]:
    """
    Generate platform-specific summaries using OpenAI if available, otherwise fallback.
    Returns dict with x_text, linkedin_text, and char_counts.
    """
    domain = item.source_domain or "news"
    title = item.title.strip()
    link = item.link.strip()
    
    if OPENAI_API_KEY:
        try:
            logger.info("🤖 Using OpenAI for dual-platform summarization")
            return summarize_with_openai_dual(title, link, domain)
        except Exception as e:
            logger.warning(f"⚠️ OpenAI summarization failed, using fallback: {e}")
    
    logger.info("Using fallback summarization")
    return summarize_fallback(item)


# ----- Notion Integration -----
def notion_client() -> Client:
    """Create a Notion client instance."""
    logger.debug("Creating Notion client")
    if not NOTION_TOKEN:
        logger.error("NOTION_TOKEN environment variable is not set")
        raise RuntimeError("NOTION_TOKEN must be set")
    
    try:
        client = Client(auth=NOTION_TOKEN)
        logger.debug("Notion client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create Notion client: {e}", exc_info=True)
        raise


def notion_create_row(notion: Client, db_id: str, *, x_text: str, linkedin_text: str,
                      scheduled_time: datetime, media_url: Optional[str] = None,
                      status: str = "Scheduled", error: Optional[str] = None):
    """
    Create a row in the Notion database with platform-specific content.
    
    Args:
        x_text: Text for X (Twitter) post (≤280 chars)
        linkedin_text: Text for LinkedIn post (≤2000 chars)
    """
    logger.debug(f"notion_create_row() called - Status: {status}, X: {len(x_text)} chars, LinkedIn: {len(linkedin_text)} chars")
    
    # Use X text for Title (backward compatibility with existing workflow)
    properties = {
        "Title": {"title": [{"type": "text", "text": {"content": x_text}}]},
        "Scheduled Time": {"date": {"start": scheduled_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')}},
        "Status": {"select": {"name": status}},
        "X URL": {"url": None},
        "LinkedIn URL": {"url": None},
    }
    
    # Add LinkedIn text as rich_text property (for platform-specific posting)
    # Note: If "LinkedIn Text" property doesn't exist in Notion DB, this will be ignored
    # The main.py script will use Title for X and can optionally use LinkedIn Text property
    if linkedin_text and linkedin_text != x_text:
        properties["LinkedIn Text"] = {
            "rich_text": [{"type": "text", "text": {"content": linkedin_text[:2000]}}]  # Notion rich_text limit
        }
        logger.debug(f"Added LinkedIn-specific text property ({len(linkedin_text)} chars)")
    
    if media_url:
        properties["Media URL"] = {"url": media_url}
        logger.debug(f"Added media URL: {media_url}")
    
    if error:
        properties["Error Log"] = {"rich_text": [{"type": "text", "text": {"content": error[:1800]}}]}
        logger.debug(f"Added error log (truncated to 1800 chars)")
    
    logger.debug(f"Creating Notion page in database: {db_id[:8]}...")
    logger.debug(f"Properties: {list(properties.keys())}")
    
    try:
        response = notion.pages.create(parent={"database_id": db_id}, properties=properties)
        page_id = response.get("id", "unknown")
        logger.info(f"✅ Notion page created successfully - ID: {page_id}")
        logger.debug(f"Notion response keys: {list(response.keys())}")
        return response
    except Exception as e:
        logger.error(f"❌ Failed to create Notion page: {type(e).__name__}: {e}", exc_info=True)
        raise


def write_skipped_row():
    """Write a Skipped row to Notion when no fresh items are found."""
    try:
        notion = notion_client()
        db_id = os.environ["NOTION_DB_ID"]
        skipped_text = "(No fresh AI news today.) (system)"
        notion_create_row(
            notion, db_id,
            x_text=skipped_text,
            linkedin_text=skipped_text,
            scheduled_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            status="Skipped",
        )
        logger.info("Wrote Skipped row to Notion.")
    except Exception as e:
        logger.error("Failed to write Skipped row: %s", e)


def create_notion_entry(summaries: Dict[str, Any], item: NewsItem, dry_run: bool = False) -> bool:
    """
    Create a Notion database entry with Status=Scheduled and platform-specific content.
    
    Args:
        summaries: Dict with x_text, linkedin_text, and char_counts
        item: NewsItem object with article metadata
        dry_run: If True, skip actual Notion API call
    """
    if dry_run:
        logger.info("🧪 DRY RUN: Skipping Notion entry creation")
        logger.info(f"   🐦 X text ({summaries['char_counts']['x']} chars): {summaries['x_text']}")
        logger.info(f"   💼 LinkedIn text ({summaries['char_counts']['linkedin']} chars):")
        logger.info(f"      {summaries['linkedin_text'][:200]}...")
        return True
    
    if not NOTION_TOKEN or not NOTION_DB_ID:
        raise RuntimeError("NOTION_TOKEN and NOTION_DB_ID must be set")
    
    scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    try:
        notion = notion_client()
        notion_create_row(
            notion, NOTION_DB_ID,
            x_text=summaries["x_text"],
            linkedin_text=summaries["linkedin_text"],
            scheduled_time=scheduled_time,
            media_url=item.image_url,
            status="Scheduled",
        )
        logger.info(f"✅ Created Notion entry for: {item.title[:50]}...")
        logger.info(f"   📊 Char counts - X: {summaries['char_counts']['x']}, LinkedIn: {summaries['char_counts']['linkedin']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create Notion entry: {e}")
        # Try to create error entry
        try:
            notion = notion_client()
            error_text = f"[ERROR] Failed to create entry for: {item.title[:100]}"
            notion_create_row(
                notion, NOTION_DB_ID,
                x_text=error_text,
                linkedin_text=error_text,
                scheduled_time=scheduled_time,
                status="Failed",
                error=str(e),
            )
            logger.info("Created error entry in Notion")
        except Exception as e2:
            logger.error(f"Failed to create error entry: {e2}")
        return False


# ----- Main -----
def main():
    parser = argparse.ArgumentParser(description="AI Content Fetcher")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing to Notion")
    args = parser.parse_args()
    
    logger.info("=== AI Content Fetcher Started ===")
    logger.info(f"Dry run mode: {args.dry_run}")
    
    try:
        # 1. Parse feeds (with Notion duplicate checking)
        items = parse_feeds()
        
        if not items:
            logger.warning("No items found in any feed")
            if not args.dry_run:
                write_skipped_row()
            return 0
        
        # Get recent Notion content for scoring
        notion_recent = set()
        if NOTION_TOKEN and NOTION_DB_ID:
            try:
                notion = notion_client()
                notion_recent = get_recent_notion_content(notion, NOTION_DB_ID, days=7)
            except Exception as e:
                logger.warning(f"Could not fetch Notion history for scoring: {e}")
        
        # 2. Score and filter with enhanced diversity and freshness checks
        scored_items = score_items(items, notion_recent=notion_recent)
        
        if not scored_items:
            logger.warning(f"No items within last {MAX_ARTICLE_AGE_HOURS}h")
            if args.dry_run:
                print("No fresh items (≤48h); Skipped.")
                return 0
            write_skipped_row()
            print("No fresh items (≤48h); Skipped.")
            return 0
        
        # 3. Pick top item
        top_item = scored_items[0]
        logger.info(f"Selected top item (score={top_item.score:.2f}): {top_item.title}")
        logger.info(f"  Link: {top_item.link}")
        logger.info(f"  Published: {top_item.published}")
        logger.info(f"  Source: {top_item.source_domain}")
        
        # 4. Summarize with platform-specific content
        summaries = summarize_item(top_item)
        logger.info(f"📝 Generated platform-specific summaries:")
        logger.info(f"   🐦 X: {summaries['char_counts']['x']} chars")
        logger.info(f"   💼 LinkedIn: {summaries['char_counts']['linkedin']} chars")
        
        # 5. Dry-run output
        if args.dry_run:
            print(json.dumps({
                "x_text": summaries["x_text"],
                "linkedin_text": summaries["linkedin_text"],
                "char_counts": summaries["char_counts"],
                "title": top_item.title,
                "link": top_item.link,
                "published": top_item.published.isoformat() if top_item.published else None,
                "image_url": top_item.image_url,
                "domain": top_item.source_domain,
                "note": "dry-run: Notion write skipped"
            }, ensure_ascii=False, indent=2))
            return 0
        
        # 6. Create Notion entry
        success = create_notion_entry(summaries, top_item, dry_run=args.dry_run)
        
        if success:
            logger.info("=== AI Content Fetcher Completed Successfully ===")
        else:
            logger.error("=== AI Content Fetcher Completed with Errors ===")
            sys.exit(1)
    
    except Exception as e:
        logger.exception("Fatal error in AI Content Fetcher")
        
        # Try to log error to Notion
        if not args.dry_run and NOTION_TOKEN and NOTION_DB_ID:
            try:
                notion = Client(auth=NOTION_TOKEN)
                scheduled_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
                error_text = "[ERROR] AI Content Fetcher failed"
                notion.pages.create(
                    parent={"database_id": NOTION_DB_ID},
                    properties={
                        "Title": {
                            "title": [{"text": {"content": error_text}}]
                        },
                        "Status": {"select": {"name": "Failed"}},
                        "Error Log": {"rich_text": [{"text": {"content": str(e)[:1800]}}]},
                        "Scheduled Time": {"date": {"start": scheduled_iso}},
                        "X URL": {"url": None},
                        "LinkedIn URL": {"url": None},
                    }
                )
            except:
                pass
        
        sys.exit(1)


if __name__ == "__main__":
    main()
