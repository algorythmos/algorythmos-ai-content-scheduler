#!/usr/bin/env python3
"""
AI Research Paper Fetcher
Fetches state-of-the-art AI research papers from arXiv, scores by relevance and novelty,
summarizes key innovations with GPT-4o-mini, and creates Notion entries for automated posting.
Focuses on cs.AI and cs.LG categories for cutting-edge ML/AI research.
"""

import os
import sys
import json
import logging
import argparse
import time
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter

import arxiv
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

# Removed PDF parsing - abstracts are sufficient for SOTA detection
# and avoid timeout/memory risks with large PDFs

# ----- Config -----
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# arXiv search parameters
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]  # AI, ML, NLP, Computer Vision
ARXIV_MAX_RESULTS = 100  # Fetch more to score and filter
ARXIV_MAX_AGE_DAYS = 7  # Only papers from last 7 days

# Research-focused keywords (SOTA, innovations, methods)
# Research-focused keywords (SOTA, innovations, methods)
BOOST_KEYWORDS = [
    "state-of-the-art", "SOTA", "novel", "breakthrough", "outperforms",
    "large language model", "LLM", "GPT", "transformer", "diffusion",
    "reinforcement learning", "RL", "neural network", "deep learning",
    "fine-tuning", "RLHF", "instruction", "reasoning", "emergent",
    "multimodal", "vision-language", "agents", "planning"
]

# Innovation indicators (higher weight for impact)
INNOVATION_KEYWORDS = [
    "state-of-the-art", "SOTA", "novel", "breakthrough", "first",
    "outperforms", "surpasses", "exceeds", "achieves", "improves",
    "new", "introduces", "proposes"
]

# Hot AI topics (trending research areas)
HOT_TOPICS = [
    "llm", "large language model", "gpt", "transformer",
    "diffusion", "diffusion model",
    "agent", "autonomous agent", "multi-agent",
    "reasoning", "chain-of-thought",
    "multimodal", "vision-language", "vlm"
]

# Prestige organizations (high-impact research)
PRESTIGE_ORGS = [
    "Google", "DeepMind", "Google DeepMind", "Google Research", "Google Brain",
    "OpenAI", "Meta AI", "Meta", "Facebook AI",
    "Microsoft Research", "Microsoft",
    "Anthropic",
    "Stanford", "Stanford University",
    "MIT", "Massachusetts Institute",
    "UC Berkeley", "Berkeley",
    "Carnegie Mellon", "CMU",
    "NVIDIA", "NVIDIA Research"
]

MAX_ARTICLE_AGE_HOURS = 168  # 7 days in hours
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
class ResearchPaper:
    """Data model for AI research papers from arXiv."""
    def __init__(
        self,
        title: str,
        arxiv_id: str,
        pdf_url: str,
        published: datetime,
        authors: List[str],
        abstract: str,
        categories: List[str],
        primary_category: str = None
    ):
        self.title = title
        self.arxiv_id = arxiv_id
        self.pdf_url = pdf_url
        self.published = published
        self.authors = authors
        self.abstract = abstract
        self.categories = categories
        self.primary_category = primary_category or (categories[0] if categories else "cs.AI")
        self.score = 0.0
        self.full_text = None  # Optional: extracted PDF text

    def __repr__(self):
        return f"<ResearchPaper '{self.title[:50]}...' arXiv:{self.arxiv_id} score={self.score:.2f}>"


# ----- arXiv Paper Fetching -----
def fetch_arxiv_papers() -> List[ResearchPaper]:
    """
    Fetch recent AI/ML research papers from arXiv.
    Queries cs.AI, cs.LG, cs.CL, cs.CV categories for papers from last 7 days.
    """
    logger.info(f"🔍 Fetching papers from arXiv (categories: {', '.join(ARXIV_CATEGORIES)})")
    
    # Build search query for multiple categories
    category_query = " OR ".join([f"cat:{cat}" for cat in ARXIV_CATEGORIES])
    
    logger.debug(f"arXiv query: {category_query}")
    logger.debug(f"Max results: {ARXIV_MAX_RESULTS}, Max age: {ARXIV_MAX_AGE_DAYS} days")
    
    papers = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=ARXIV_MAX_AGE_DAYS)
    
    try:
        # Create arXiv client and search
        client = arxiv.Client()
        search = arxiv.Search(
            query=category_query,
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.SubmittedDate,  # Most recent first
            sort_order=arxiv.SortOrder.Descending
        )
        
        logger.info(f"📡 Querying arXiv API...")
        
        for result in client.results(search):
            # Filter by age
            if result.published < cutoff:
                logger.debug(f"Skipping old paper: {result.title[:50]}... ({result.published})")
                continue
            
            # Extract data
            paper = ResearchPaper(
                title=result.title.strip(),
                arxiv_id=result.entry_id.split('/')[-1],  # Extract ID from URL
                pdf_url=result.pdf_url,
                published=result.published,
                authors=[author.name for author in result.authors],
                abstract=result.summary.strip(),
                categories=result.categories,
                primary_category=result.primary_category
            )
            
            papers.append(paper)
            logger.debug(f"Added paper: {paper.arxiv_id} - {paper.title[:60]}...")
        
        logger.info(f"✅ Fetched {len(papers)} papers from last {ARXIV_MAX_AGE_DAYS} days")
        
        if papers:
            logger.info(f"📊 Date range: {min(p.published for p in papers)} to {max(p.published for p in papers)}")
        
        return papers
    
    except Exception as e:
        logger.error(f"❌ Failed to fetch arXiv papers: {e}", exc_info=True)
        return []


# Removed extract_pdf_text() - arXiv abstracts are structured, dense, and sufficient
# for SOTA detection. Avoids PDF download latency, memory issues, and parsing failures.
def get_recent_notion_content(notion: Client, db_id: str, days: int = 7) -> Set[Tuple[str, str]]:
    """
    Query Notion for recent Posted/Scheduled/Failed entries to prevent duplicates.
    Returns set of (normalized_title, arxiv_id) tuples.
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
                    # Try to extract arXiv ID if present
                    arxiv_id = ""
                    arxiv_prop = page["properties"].get("arXiv ID", {})
                    if arxiv_prop:
                        arxiv_text = arxiv_prop.get("rich_text", [])
                        if arxiv_text:
                            arxiv_id = "".join(b.get("plain_text", "") for b in arxiv_text)
                    
                    seen_content.add((normalized, arxiv_id))
        
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


def score_papers(papers: List[ResearchPaper], notion_recent: Optional[Set[Tuple[str, str]]] = None) -> List[ResearchPaper]:
    """
    Score research papers by relevance, novelty, impact, and recency.
    Returns sorted list (highest score first).
    
    Scoring factors:
    - Recency: <24h +20pts, 24-48h +15pts, 48-96h +10pts, 96-168h +5pts
    - SOTA detection: +25pts (outperforms, state-of-the-art in abstract)
    - Innovation keywords: +5pts each (novel, breakthrough, introduces, etc.)
    - Hot topics: +10pts (LLM, diffusion, agent, reasoning, multimodal)
    - General keywords: +2pts each (transformer, RL, fine-tuning, etc.)
    - Category match: +3pts for cs.AI/cs.LG primary
    - Abstract quality: -15pts if <300 chars (low quality filter)
    - Prestige org: +20pts (Google/DeepMind/OpenAI/Stanford/MIT/etc.)
    - Duplicate penalty: -100pts for exact arXiv ID match
    """
    logger.info(f"📊 Scoring {len(papers)} papers with enhanced impact filters...")
    
    now = datetime.now(timezone.utc)
    filtered_papers = []
    
    for paper in papers:
        score = 0.0
        
        # Calculate age in hours
        age_h = (now - paper.published).total_seconds() / 3600
        
        # Recency boost (research is time-sensitive)
        if 0 <= age_h <= 24:
            score += 20  # Brand new (< 24h)
        elif age_h <= 48:
            score += 15  # Very fresh (24-48h)
        elif age_h <= 96:
            score += 10  # Fresh (48-96h / 2-4 days)
        elif age_h <= 168:
            score += 5   # Recent (96-168h / 4-7 days)
        else:
            score -= 100  # Too old (shouldn't happen with 7-day filter)
        
        # Prepare text for keyword matching
        title_abstract = (paper.title + " " + paper.abstract).upper()
        abstract_lower = paper.abstract.lower()
        
        # SOTA detection (high impact indicator)
        if "SOTA" in title_abstract or "state-of-the-art" in abstract_lower or \
           "outperforms" in abstract_lower or "surpasses" in abstract_lower:
            score += 25
            logger.debug(f"✨ SOTA detected: {paper.title[:50]}...")
        
        # Innovation keyword matching (high weight)
        innovation_count = sum(1 for kw in INNOVATION_KEYWORDS if kw.upper() in title_abstract)
        score += innovation_count * 5
        
        if innovation_count > 0:
            logger.debug(f"💡 {innovation_count} innovation keywords in: {paper.title[:40]}...")
        
        # Hot topics boost (trending research areas)
        hot_topic_match = any(ht in abstract_lower for ht in HOT_TOPICS)
        if hot_topic_match:
            score += 10
            logger.debug(f"🔥 Hot topic detected: {paper.title[:40]}...")
        
        # General keyword matching
        general_count = sum(1 for kw in BOOST_KEYWORDS if kw.upper() in title_abstract)
        score += general_count * 2
        
        # Category boost (prefer core AI/ML)
        if paper.primary_category in ["cs.AI", "cs.LG"]:
            score += 3
            logger.debug(f"📚 Category boost ({paper.primary_category}): {paper.title[:40]}...")
        
        # Abstract quality filter (penalize short/low-quality abstracts)
        if len(paper.abstract) < 300:
            score -= 15
            logger.debug(f"⚠️ Short abstract penalty ({len(paper.abstract)} chars): {paper.title[:40]}...")
        
        # Prestige organization boost (high-impact authors)
        authors_str = " ".join(paper.authors)
        if any(org in authors_str for org in PRESTIGE_ORGS):
            score += 20
            matching_org = next(org for org in PRESTIGE_ORGS if org in authors_str)
            logger.debug(f"🏛️ Prestige org ({matching_org}): {paper.title[:40]}...")
        
        # Check similarity with recent Notion content
        if notion_recent:
            norm_title = normalize_title(paper.title)
            for notion_title, notion_arxiv_id in notion_recent:
                # Check arXiv ID match (exact duplicate)
                if notion_arxiv_id and notion_arxiv_id == paper.arxiv_id:
                    penalty = 100  # Heavy penalty for exact duplicate
                    score -= penalty
                    logger.debug(f"❌ Duplicate arXiv ID ({paper.arxiv_id}): -{penalty}pts")
                    break
                
                # Check title similarity
                similarity = title_similarity(norm_title, notion_title)
                if similarity > 0.6:  # High similarity threshold
                    penalty = (similarity - 0.6) * 25  # Strong penalty
                    score -= penalty
                    logger.debug(f"⚠️ Similar title penalty: -{penalty:.2f}pts for '{paper.title[:40]}...'")
                    break
        
        paper.score = score
        filtered_papers.append(paper)
    
    # Sort by score descending
    filtered_papers.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"✅ Scored and sorted {len(filtered_papers)} papers")
    
    # Log top 5 for debugging
    if filtered_papers:
        logger.info("🏆 Top 5 scored papers:")
        for i, paper in enumerate(filtered_papers[:5], 1):
            age_h = (now - paper.published).total_seconds() / 3600
            logger.info(f"  {i}. [Score: {paper.score:.1f}] {paper.title[:60]}...")
            logger.info(f"     arXiv:{paper.arxiv_id}, {paper.primary_category}, {age_h:.1f}h old")
    
    return filtered_papers


# ----- OLD UNUSED RSS CODE (TO BE REMOVED) -----
# These functions are from the old news RSS approach and are no longer used.
# The system now uses arXiv research papers exclusively.

def old_parse_feeds_placeholder():
    """
    OLD: RSS feed parsing - replaced by fetch_arxiv_papers()
    Fetch and parse all RSS feeds, returning normalized NewsItem objects.
    Enhanced with:
    - Notion duplicate checking
    - Exponential backoff retries
    - Better deduplication
    """
    pass  # Removed - using arXiv instead


def old_score_items_placeholder():
    
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


# ----- Scoring ----- (OLD - COMMENTED OUT)
# def score_items(items: List[NewsItem], notion_recent: Optional[Set[Tuple[str, str]]] = None) -> List[NewsItem]:
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
def summarize_with_openai_dual(paper: ResearchPaper) -> Dict[str, Any]:
    """
    Use OpenAI to generate platform-specific summaries for research papers.
    Returns dict with: {"x_text": str, "linkedin_text": str, "char_counts": dict}
    """
    logger.debug(f"summarize_with_openai_dual() called for: {paper.title[:50]}...")
    
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
    
    # Professional research-focused prompt with metric-driven templates
    sys_msg = """You are a senior AI researcher at Algorythmos. Summarize cutting-edge arXiv papers for professional audiences on X (Twitter) and LinkedIn. Generate TWO versions with strict formatting:

**X VERSION (≤280 chars total):**
Format: "SOTA in [Domain]: [Paper Title] achieves [X]% over prior best

• Method: [1-line explanation]
• Key: [innovation]

by [Lead Author] et al.

#AI #ML #Research
https://arxiv.org/abs/[ID]"

**LinkedIn VERSION (≤2000 chars total):**
Format:
"New Breakthrough in AI Research

[Title]

Authors: [Author 1], [Author 2], ... ([Institution])
arXiv: [ID] | Submitted: [Date]

Key Innovation:
→ [One-sentence punchline]

Method:
• [Brief 2-3 bullet explanation]

Results:
• +X% on [Benchmark]
• SOTA on [Dataset 1], [Dataset 2]

Why it matters for Algorythmos:
This [method/technique] could power next-gen automation in our MLOps platform.

Read the paper: https://arxiv.org/abs/[ID]

What do you think — ready for production? Let's discuss.

#AI #MachineLearning #DeepLearning #Research #MLOps"

**CRITICAL RULES:**
1. Include QUANTITATIVE results (metrics, %, benchmarks) whenever mentioned in abstract
2. Highlight SOTA claims explicitly
3. For X: Focus on breakthrough + metric + method (1 line each)
4. For LinkedIn: Use bullet structure, explain implications for MLOps/automation
5. Extract lead author and institution from author list
6. Always end LinkedIn with engagement question
7. Count characters EXACTLY (including spaces, emojis, newlines)

Output STRICTLY as valid JSON (no markdown, no code blocks, no extra text):
{
  "x_text": "[complete X post ≤280 chars]",
  "linkedin_text": "[complete LinkedIn post ≤2000 chars]",
  "char_counts": {
    "x": [exact count],
    "linkedin": [exact count]
  }
}"""
    
    # Prepare paper context for LLM
    authors_str = ", ".join(paper.authors[:3])  # First 3 authors
    if len(paper.authors) > 3:
        authors_str += f" et al. ({len(paper.authors)} authors)"
    
    user_msg = f"""Research Paper Details:

Title: {paper.title}
Authors: {authors_str}
arXiv ID: {paper.arxiv_id}
Categories: {', '.join(paper.categories[:3])}
Published: {paper.published.strftime('%Y-%m-%d')}

Abstract:
{paper.abstract}

arXiv Link: https://arxiv.org/abs/{paper.arxiv_id}

Generate engaging social media content highlighting the key innovations and SOTA contributions."""
    
    logger.debug(f"Sending request to OpenAI - Model: {OPENAI_MODEL}")
    logger.debug(f"Paper: {paper.arxiv_id}, Abstract length: {len(paper.abstract)} chars")
    
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,  # Balanced creativity for research communication
            max_tokens=1500,  # Support longer LinkedIn posts
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
        
        logger.info(f"✅ Generated dual-platform research summaries:")
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


def summarize_fallback(paper: ResearchPaper) -> Dict[str, Any]:
    """
    Professional fallback summarization when OpenAI is unavailable.
    Uses structured templates matching the LLM prompt format.
    """
    logger.debug(f"summarize_fallback() called for: {paper.title[:50]}...")
    
    # Extract lead author and institution (best effort)
    lead_author = paper.authors[0] if paper.authors else "Unknown"
    if " " in lead_author:
        lead_author = lead_author.split()[-1]  # Last name
    
    authors_short = lead_author
    if len(paper.authors) > 1:
        authors_short += " et al."
    
    # Generate X version with professional SOTA format
    category_name = paper.primary_category.replace('cs.', '').upper()
    x_text = f"New {category_name} research: {paper.title[:120]}... by {authors_short}\n\n#AI #ML #Research\narXiv:{paper.arxiv_id}"
    
    if len(x_text) > MAX_X_CHARS:
        # Truncate title to fit
        max_title = MAX_X_CHARS - len(f"New {category_name} research: ... by {authors_short}\n\n#AI #ML\narXiv:{paper.arxiv_id}")
        x_text = f"New {category_name} research: {paper.title[:max_title]}... by {authors_short}\n\n#AI #ML\narXiv:{paper.arxiv_id}"
    
    # Generate LinkedIn version with professional structure
    authors_list = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors_list += f" et al."
    
    # Extract first author institution (if available in parentheses)
    institution = "Research Team"
    if "(" in paper.authors[0]:
        institution = paper.authors[0].split("(")[-1].split(")")[0]
    
    linkedin_text = f"""New Breakthrough in AI Research

{paper.title}

Authors: {authors_list}
arXiv: {paper.arxiv_id} | Submitted: {paper.published.strftime('%B %d, %Y')}

Key Innovation:
→ {paper.abstract[:200].strip()}...

Method:
• Novel approach in {paper.primary_category.replace('cs.', '')} research
• Published in {', '.join(paper.categories[:2])}

Abstract Summary:
{paper.abstract[:600].strip()}{'...' if len(paper.abstract) > 600 else ''}

Why it matters for Algorythmos:
This research could inform next-generation AI automation workflows and MLOps practices.

Read the full paper: https://arxiv.org/abs/{paper.arxiv_id}

What are your thoughts on this approach? Ready for production?

#AI #MachineLearning #DeepLearning #Research #MLOps"""
    
    if len(linkedin_text) > MAX_LINKEDIN_CHARS:
        # Truncate abstract section if too long
        linkedin_text = linkedin_text[:MAX_LINKEDIN_CHARS - 3] + "..."
    
    logger.info(f"Generated professional fallback summaries: X={len(x_text)} chars, LinkedIn={len(linkedin_text)} chars")
    
    return {
        "x_text": x_text,
        "linkedin_text": linkedin_text,
        "char_counts": {
            "x": len(x_text),
            "linkedin": len(linkedin_text)
        }
    }


def summarize_paper(paper: ResearchPaper) -> Dict[str, Any]:
    """
    Generate platform-specific summaries using OpenAI if available, otherwise fallback.
    Returns dict with x_text, linkedin_text, and char_counts.
    """
    if OPENAI_API_KEY:
        try:
            logger.info("🤖 Using OpenAI for dual-platform research summarization")
            return summarize_with_openai_dual(paper)
        except Exception as e:
            logger.warning(f"⚠️ OpenAI summarization failed, using fallback: {e}")
    
    logger.info("Using fallback summarization for research paper")
    return summarize_fallback(paper)


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


def create_notion_entry(summaries: Dict[str, Any], paper: ResearchPaper, dry_run: bool = False) -> bool:
    """
    Create a Notion database entry with Status=Scheduled and platform-specific content.
    
    Args:
        summaries: Dict with x_text, linkedin_text, and char_counts
        paper: ResearchPaper object with arXiv metadata
        dry_run: If True, skip actual Notion API call
    """
    if dry_run:
        logger.info("🧪 DRY RUN: Skipping Notion entry creation")
        logger.info(f"   📄 Paper: {paper.title}")
        logger.info(f"   🔬 arXiv: {paper.arxiv_id}")
        logger.info(f"   👥 Authors: {', '.join(paper.authors[:3])}")
        logger.info(f"   📊 Score: {paper.score:.1f}")
        logger.info(f"   🐦 X text ({summaries['char_counts']['x']} chars): {summaries['x_text'][:100]}...")
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
            media_url=None,  # No PDF downloads anymore
            status="Scheduled",
        )
        logger.info(f"✅ Created Notion entry for paper: {paper.arxiv_id}")
        logger.info(f"   📊 Char counts - X: {summaries['char_counts']['x']}, LinkedIn: {summaries['char_counts']['linkedin']}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create Notion entry: {e}")
        # Try to create error entry
        try:
            notion = notion_client()
            error_text = f"[ERROR] Failed to create entry for paper: {paper.arxiv_id} - {paper.title[:80]}"
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
    parser = argparse.ArgumentParser(description="AI Research Paper Fetcher")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing to Notion")
    args = parser.parse_args()
    
    logger.info("=== AI Research Paper Fetcher Started ===")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"arXiv categories: {', '.join(ARXIV_CATEGORIES)}")
    logger.info(f"Max papers to fetch: {ARXIV_MAX_RESULTS}")
    logger.info(f"Max age: {ARXIV_MAX_AGE_DAYS} days")
    
    try:
        # 1. Fetch recent arXiv papers
        papers = fetch_arxiv_papers()
        
        if not papers:
            logger.warning("No papers found from arXiv")
            if not args.dry_run:
                write_skipped_row()
            return 0
        
        # Get recent Notion content for duplicate detection
        notion_recent = set()
        if NOTION_TOKEN and NOTION_DB_ID:
            try:
                notion = notion_client()
                notion_recent = get_recent_notion_content(notion, NOTION_DB_ID, days=7)
                logger.info(f"📚 Found {len(notion_recent)} recent entries in Notion for duplicate checking")
            except Exception as e:
                logger.warning(f"Could not fetch Notion history for scoring: {e}")
        
        # 2. Score papers with enhanced impact filters
        scored_papers = score_papers(papers, notion_recent=notion_recent)
        
        if not scored_papers:
            logger.warning(f"No papers passed scoring filters")
            if args.dry_run:
                print("No high-quality papers found; Skipped.")
                return 0
            write_skipped_row()
            print("No high-quality papers found; Skipped.")
            return 0
        
        # 3. Pick top paper
        top_paper = scored_papers[0]
        logger.info(f"🏆 Selected top paper (score={top_paper.score:.1f}):")
        logger.info(f"   📄 Title: {top_paper.title}")
        logger.info(f"   🔬 arXiv: {top_paper.arxiv_id}")
        logger.info(f"   👥 Authors: {', '.join(top_paper.authors[:3])}")
        logger.info(f"   📅 Published: {top_paper.published}")
        logger.info(f"   📚 Category: {top_paper.primary_category}")
        
        # 4. Generate professional summaries with metrics
        summaries = summarize_paper(top_paper)
        logger.info(f"📝 Generated professional platform-specific summaries:")
        logger.info(f"   🐦 X: {summaries['char_counts']['x']}/{MAX_X_CHARS} chars")
        logger.info(f"   💼 LinkedIn: {summaries['char_counts']['linkedin']}/{MAX_LINKEDIN_CHARS} chars")
        
        # 5. Dry-run output (JSON format)
        if args.dry_run:
            output = {
                "x_text": summaries["x_text"],
                "linkedin_text": summaries["linkedin_text"],
                "char_counts": summaries["char_counts"],
                "paper": {
                    "title": top_paper.title,
                    "arxiv_id": top_paper.arxiv_id,
                    "arxiv_url": f"https://arxiv.org/abs/{top_paper.arxiv_id}",
                    "published": top_paper.published.isoformat(),
                    "authors": top_paper.authors[:5],
                    "categories": top_paper.categories,
                    "abstract": top_paper.abstract[:300] + "...",
                    "score": round(top_paper.score, 2)
                },
                "note": "🧪 DRY RUN: Notion write skipped"
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        
        # 6. Create Notion entry
        success = create_notion_entry(summaries, top_paper, dry_run=args.dry_run)
        
        if success:
            logger.info("=== AI Research Paper Fetcher Completed Successfully ===")
            logger.info(f"✅ Scheduled paper {top_paper.arxiv_id} for posting")
        else:
            logger.error("=== AI Research Paper Fetcher Completed with Errors ===")
            sys.exit(1)
    
    except Exception as e:
        logger.exception("Fatal error in AI Research Paper Fetcher")
        
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
