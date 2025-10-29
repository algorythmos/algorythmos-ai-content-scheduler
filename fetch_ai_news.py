#!/usr/bin/env python3
"""
Algorythmos AI Research Digest v3.0
====================================
Top arXiv AI Papers → GPT-4o-mini → Notion → X & LinkedIn

"We don't post news. We post breakthroughs."

Author: Algorythmos
License: MIT
"""

import os
import sys
import json
import logging
import argparse
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set, Tuple

import arxiv
import requests
from dateutil import parser as date_parser
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Optional OpenAI integration
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ==============================
# CONFIGURATION & CONSTANTS
# ==============================

# Environment variables
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# arXiv search parameters
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]
ARXIV_MAX_RESULTS = 100
ARXIV_MAX_AGE_DAYS = 7

# Platform-specific character limits
MAX_X_CHARS = 280
MAX_LINKEDIN_CHARS = 2000

# Scoring weights
RECENCY_BOOST = {
    24: 20,   # <24h: Brand new papers
    48: 15,   # 24-48h: Very fresh
    96: 10,   # 48-96h: Fresh
    168: 5    # 96-168h: Recent
}

# Research-focused keywords
INNOVATION_KEYWORDS = [
    "state-of-the-art", "SOTA", "novel", "breakthrough", "first",
    "outperforms", "surpasses", "exceeds", "achieves", "improves",
    "new", "introduces", "proposes"
]

HOT_TOPICS = [
    "llm", "large language model", "gpt", "transformer",
    "diffusion", "diffusion model",
    "agent", "autonomous agent", "multi-agent",
    "reasoning", "chain-of-thought",
    "multimodal", "vision-language", "vlm"
]

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

# Logging configuration
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level,
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ==============================
# DATA MODEL
# ==============================

class ResearchPaper:
    """Data model for AI research papers from arXiv."""
    
    def __init__(self, result: arxiv.Result):
        self.title = result.title.strip()
        self.arxiv_id = result.entry_id.split("/")[-1].split("v")[0]
        self.pdf_url = result.pdf_url
        self.authors = [author.name for author in result.authors]
        self.abstract = result.summary.strip()
        self.categories = result.categories
        self.primary_category = result.primary_category
        self.published = result.published
        self.score = 0.0
        self.institutions = self._extract_institutions()

    def _extract_institutions(self) -> List[str]:
        """Extract prestige institutions from author affiliations."""
        institutions = []
        authors_str = " ".join(self.authors)
        for org in PRESTIGE_ORGS:
            if org in authors_str:
                institutions.append(org)
        return list(set(institutions))

    def to_dict(self) -> Dict[str, Any]:
        """Convert paper to dictionary format."""
        return {
            "title": self.title,
            "arxiv_id": self.arxiv_id,
            "arxiv_url": f"https://arxiv.org/abs/{self.arxiv_id}",
            "published": self.published.isoformat(),
            "authors": self.authors[:5],
            "categories": self.categories,
            "primary_category": self.primary_category,
            "abstract": self.abstract[:300] + "...",
            "score": round(self.score, 2),
            "institutions": self.institutions
        }

# ==============================
# ARXIV FETCHING
# ==============================

def fetch_arxiv_papers() -> List[ResearchPaper]:
    """Fetch recent papers from arXiv in target categories."""
    logger.info(f"🔍 Fetching papers from arXiv (categories: {', '.join(ARXIV_CATEGORIES)})")
    
    # Build query for multiple categories
    query = " OR ".join([f"cat:{cat}" for cat in ARXIV_CATEGORIES])
    
    search = arxiv.Search(
        query=query,
        max_results=ARXIV_MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    papers = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=ARXIV_MAX_AGE_DAYS)
    
    logger.info("📡 Querying arXiv API...")
    
    for result in search.results():
        # Filter papers by age
        if result.published < cutoff:
            continue
        
        paper = ResearchPaper(result)
        papers.append(paper)
    
    logger.info(f"✅ Fetched {len(papers)} papers from last {ARXIV_MAX_AGE_DAYS} days")
    
    if papers:
        oldest = min(p.published for p in papers)
        newest = max(p.published for p in papers)
        logger.info(f"📊 Date range: {oldest} to {newest}")
    
    return papers

# ==============================
# SCORING
# ==============================

def score_papers(papers: List[ResearchPaper], notion_recent: Optional[Set[Tuple[str, str]]] = None) -> List[ResearchPaper]:
    """
    Score research papers by relevance, novelty, impact, and recency.
    Returns sorted list (highest score first).
    
    Scoring factors:
    - Recency: <24h +20pts, 24-48h +15pts, 48-96h +10pts, 96-168h +5pts
    - SOTA detection: +25pts (outperforms, state-of-the-art in abstract)
    - Innovation keywords: +5pts each (novel, breakthrough, introduces, etc.)
    - Hot topics: +10pts (LLM, diffusion, agent, reasoning, multimodal)
    - Prestige org: +20pts (Google/DeepMind/OpenAI/Stanford/MIT/etc.)
    - Abstract quality: -15pts if <300 chars (low quality filter)
    - Duplicate penalty: -100pts for exact arXiv ID match
    """
    logger.info(f"📊 Scoring {len(papers)} papers with enhanced impact filters...")
    
    now = datetime.now(timezone.utc)
    
    for paper in papers:
        score = 0.0
        
        # Calculate age in hours
        age_h = (now - paper.published).total_seconds() / 3600
        
        # 1. Recency boost
        for hours, boost in RECENCY_BOOST.items():
            if age_h < hours:
                score += boost
                break
        
        # Prepare text for keyword matching
        title_abstract = (paper.title + " " + paper.abstract).upper()
        abstract_lower = paper.abstract.lower()
        
        # 2. SOTA detection (high impact indicator)
        if "SOTA" in title_abstract or "state-of-the-art" in abstract_lower or \
           "outperforms" in abstract_lower or "surpasses" in abstract_lower:
            score += 25
            logger.debug(f"✨ SOTA detected: {paper.title[:50]}...")
        
        # 3. Innovation keyword matching
        innovation_count = sum(1 for kw in INNOVATION_KEYWORDS if kw.upper() in title_abstract)
        score += innovation_count * 5
        
        if innovation_count > 0:
            logger.debug(f"💡 {innovation_count} innovation keywords in: {paper.title[:40]}...")
        
        # 4. Hot topics boost
        hot_topic_match = any(ht in abstract_lower for ht in HOT_TOPICS)
        if hot_topic_match:
            score += 10
            logger.debug(f"🔥 Hot topic detected: {paper.title[:40]}...")
        
        # 5. Prestige organization boost
        if paper.institutions:
            score += len(paper.institutions) * 20
            logger.debug(f"🏛️ Prestige orgs ({', '.join(paper.institutions)}): {paper.title[:40]}...")
        
        # 6. Abstract quality filter
        if len(paper.abstract) < 300:
            score -= 15
            logger.debug(f"⚠️ Short abstract penalty ({len(paper.abstract)} chars): {paper.title[:40]}...")
        
        # 7. Category boost (prefer core AI/ML)
        if paper.primary_category in ["cs.AI", "cs.LG"]:
            score += 3
        
        # 8. Check for duplicates in Notion
        if notion_recent:
            for _, notion_arxiv_id in notion_recent:
                if notion_arxiv_id and notion_arxiv_id == paper.arxiv_id:
                    score -= 100
                    logger.debug(f"❌ Duplicate arXiv ID ({paper.arxiv_id}): -{100}pts")
                    break
        
        paper.score = score
    
    # Sort by score descending
    papers.sort(key=lambda x: x.score, reverse=True)
    
    logger.info(f"✅ Scored and sorted {len(papers)} papers")
    
    # Log top 5 for debugging
    if papers:
        logger.info("🏆 Top 5 scored papers:")
        for i, paper in enumerate(papers[:5], 1):
            age_h = (now - paper.published).total_seconds() / 3600
            logger.info(f"  {i}. [Score: {paper.score:.1f}] {paper.title[:60]}...")
            logger.info(f"     arXiv:{paper.arxiv_id}, {paper.primary_category}, {age_h:.1f}h old")
    
    return papers

# ==============================
# SUMMARIZATION (OpenAI)
# ==============================

RESEARCH_PROMPT = """You are an expert AI research communicator for Algorythmos, a France-based AI automation firm. Summarize cutting-edge AI research papers for professional audiences on X (Twitter) and LinkedIn. Generate TWO versions:

1. **X (Twitter) Version**: ≤280 characters total (including spaces, emojis, hashtags). Focus on the SOTA contribution or breakthrough. Make it punchy: "New SOTA in [area]: [key innovation]". Include 1-2 hashtags like #AIResearch #MachineLearning.

2. **LinkedIn Version**: ≤2000 characters total. Professional deep-dive for AI practitioners:
   - Start with hook highlighting the innovation
   - 3-5 bullet points covering: problem, method, results/improvements, implications
   - Explain relevance to Algorythmos (e.g., "This could enhance our MLOps pipelines")
   - End with thought-provoking question for engagement
   - Use 2-3 hashtags: #AIResearch #MachineLearning #DeepLearning

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
- Focus on **innovations, SOTA results, novel methods**
- Highlight quantitative improvements if mentioned (e.g., "+15% accuracy", "10x faster")
- Explain technical concepts clearly for practitioners
- Tie to Algorythmos mission: AI automation, MLOps, enterprise AI
- Be factual, professional, and research-focused
- Do NOT include URLs in character counts (append separately)
- Keep X version under 280 chars, LinkedIn under 2000 chars"""

def summarize_with_openai(paper: ResearchPaper) -> Dict[str, Any]:
    """Generate platform-specific summaries using OpenAI GPT-4o-mini."""
    logger.debug(f"summarize_with_openai() called for: {paper.title[:50]}...")
    
    if not OPENAI_AVAILABLE or not OPENAI_API_KEY:
        logger.warning("OpenAI not available, using fallback")
        return summarize_fallback(paper)
    
    # Initialize client
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        logger.debug(f"OpenAI client initialized with model: {OPENAI_MODEL}")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {e}")
        return summarize_fallback(paper)
    
    # Prepare paper context for LLM
    authors_str = ", ".join(paper.authors[:3])
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
    
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": RESEARCH_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}
        )
        
        logger.debug(f"OpenAI API response received - Usage: {resp.usage}")
        raw_response = (resp.choices[0].message.content or "").strip()
        
        # Parse JSON response
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI JSON response: {e}")
            return summarize_fallback(paper)
        
        # Extract and validate texts
        x_text = result.get("x_text", "").strip()
        linkedin_text = result.get("linkedin_text", "").strip()
        
        if not x_text or not linkedin_text:
            logger.error(f"Missing texts in OpenAI response")
            return summarize_fallback(paper)
        
        # Validate and truncate if needed
        if len(x_text) > MAX_X_CHARS:
            logger.warning(f"⚠️ X text exceeded limit ({len(x_text)} > {MAX_X_CHARS}), truncating...")
            x_text = x_text[:MAX_X_CHARS - 3] + "..."
        
        if len(linkedin_text) > MAX_LINKEDIN_CHARS:
            logger.warning(f"⚠️ LinkedIn text exceeded limit ({len(linkedin_text)} > {MAX_LINKEDIN_CHARS}), truncating...")
            linkedin_text = linkedin_text[:MAX_LINKEDIN_CHARS - 3] + "..."
        
        logger.info(f"✅ Generated dual-platform research summaries:")
        logger.info(f"   🐦 X: {len(x_text)}/{MAX_X_CHARS} chars")
        logger.info(f"   💼 LinkedIn: {len(linkedin_text)}/{MAX_LINKEDIN_CHARS} chars")
        
        return {
            "x_text": x_text,
            "linkedin_text": linkedin_text,
            "char_counts": {
                "x": len(x_text),
                "linkedin": len(linkedin_text)
            }
        }
    
    except Exception as e:
        logger.error(f"OpenAI API error: {type(e).__name__}: {e}")
        return summarize_fallback(paper)

# ==============================
# FALLBACK SUMMARIZATION
# ==============================

def summarize_fallback(paper: ResearchPaper) -> Dict[str, Any]:
    """
    Professional fallback summarization when OpenAI is unavailable.
    Uses structured templates matching the LLM prompt format.
    """
    logger.info("Using fallback summarization for research paper")
    
    # Extract lead author
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
        max_title = MAX_X_CHARS - len(f"New {category_name} research: ... by {authors_short}\n\n#AI #ML\narXiv:{paper.arxiv_id}")
        x_text = f"New {category_name} research: {paper.title[:max_title]}... by {authors_short}\n\n#AI #ML\narXiv:{paper.arxiv_id}"
    
    # Generate LinkedIn version with professional structure
    authors_list = ", ".join(paper.authors[:3])
    if len(paper.authors) > 3:
        authors_list += f" et al."
    
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

# ==============================
# NOTION INTEGRATION
# ==============================

def get_notion_client() -> Client:
    """Create or return cached Notion client."""
    if not NOTION_TOKEN:
        raise RuntimeError("NOTION_TOKEN must be set")
    return Client(auth=NOTION_TOKEN)

def ensure_notion_schema():
    """
    Ensure all required properties exist in the Notion database.
    Self-healing: automatically creates missing properties.
    Idempotent: safe to call multiple times.
    """
    client = get_notion_client()
    db_id = NOTION_DB_ID
    
    if not db_id:
        logger.warning("NOTION_DB_ID not set, skipping schema validation")
        return
    
    # Define required properties with their types
    required_props = {
        "arXiv ID": {"rich_text": {}},
        "arXiv Link": {"url": {}},
        "Authors": {"rich_text": {}},
        "Categories": {"rich_text": {}},
        "X Text": {"rich_text": {}},
        "LinkedIn Text": {"rich_text": {}},
        "Score": {"number": {"format": "number"}},
        "Status": {"select": {"options": []}},  # Will use existing options
        "Scheduled Time": {"date": {}},
        "X URL": {"url": {}},
        "LinkedIn URL": {"url": {}},
    }

    try:
        logger.info("🔍 Checking Notion database schema...")
        db = client.databases.retrieve(database_id=db_id)
        existing = {name: prop for name, prop in db["properties"].items()}
        
        to_create = {}
        for name, config in required_props.items():
            prop_type = list(config.keys())[0]
            
            if name not in existing:
                logger.info(f"   ➕ Missing property: {name} ({prop_type})")
                to_create[name] = config
            elif existing[name]["type"] != prop_type:
                logger.warning(f"   ⚠️  Property {name} exists but wrong type: {existing[name]['type']} (expected {prop_type})")

        if to_create:
            logger.info(f"📝 Creating {len(to_create)} missing Notion properties...")
            client.databases.update(
                database_id=db_id,
                properties=to_create
            )
            logger.info("✅ Notion schema updated successfully!")
            for name in to_create.keys():
                logger.info(f"   ✓ Created: {name}")
        else:
            logger.info("✅ Notion schema already up-to-date")
            
    except Exception as e:
        logger.error(f"❌ Failed to update Notion schema: {e}")
        logger.warning("Continuing with existing schema (may cause errors if properties missing)")
        # Continue — system may still work if some props exist

def get_recent_notion_content(client: Client, db_id: str, days: int = 7) -> Set[Tuple[str, str]]:
    """
    Query Notion for recent entries to prevent duplicates.
    Returns set of (normalized_title, arxiv_id) tuples.
    """
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff.replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        
        response = client.databases.query(
            database_id=db_id,
            filter={
                "or": [
                    {"property": "Status", "select": {"equals": "Scheduled"}},
                    {"property": "Status", "select": {"equals": "Posted"}},
                    {"property": "Status", "select": {"equals": "Failed"}},
                ]
            }
        )
        
        seen = set()
        for page in response.get("results", []):
            props = page.get("properties", {})
            
            # Get title
            title_prop = props.get("Title", {}).get("title", [])
            title = title_prop[0].get("text", {}).get("content", "") if title_prop else ""
            
            # Get arXiv ID
            arxiv_prop = props.get("arXiv ID", {}).get("rich_text", [])
            arxiv_id = arxiv_prop[0].get("text", {}).get("content", "") if arxiv_prop else ""
            
            if title or arxiv_id:
                normalized_title = title.lower().strip()
                seen.add((normalized_title, arxiv_id))
        
        logger.info(f"Found {len(seen)} recent entries in Notion (last {days} days)")
        return seen
    
    except Exception as e:
        logger.warning(f"Could not fetch Notion history: {e}")
        return set()

def notion_create_row(paper: ResearchPaper, summaries: Dict[str, Any]) -> Dict[str, Any]:
    """Create a Notion database entry for the research paper."""
    if not NOTION_DB_ID:
        raise RuntimeError("NOTION_DB_ID must be set")
    
    client = get_notion_client()
    scheduled_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    
    properties = {
        "Title": {"title": [{"type": "text", "text": {"content": paper.title}}]},
        "Scheduled Time": {"date": {"start": scheduled_time.replace(microsecond=0).isoformat().replace('+00:00', 'Z')}},
        "Status": {"select": {"name": "Scheduled"}},
        "arXiv ID": {"rich_text": [{"text": {"content": paper.arxiv_id}}]},
        "arXiv Link": {"url": f"https://arxiv.org/abs/{paper.arxiv_id}"},
        "Authors": {"rich_text": [{"text": {"content": ", ".join(paper.authors[:5])}}]},
        "Categories": {"rich_text": [{"text": {"content": ", ".join(paper.categories)}}]},
        "X Text": {"rich_text": [{"text": {"content": summaries["x_text"]}}]},
        "LinkedIn Text": {"rich_text": [{"text": {"content": summaries["linkedin_text"]}}]},
        "X URL": {"url": None},
        "LinkedIn URL": {"url": None},
    }
    
    try:
        response = client.pages.create(
            parent={"database_id": NOTION_DB_ID},
            properties=properties
        )
        page_id = response["id"]
        logger.info(f"✅ Created Notion entry for paper: {paper.arxiv_id}")
        
        # Auto-set to "Ready to Post" for immediate publishing
        # Only set to "Ready" if scheduled time has passed (immediate posting)
        current_time = datetime.now(timezone.utc)
        if current_time >= scheduled_time:
            try:
                client.pages.update(
                    page_id=page_id,
                    properties={"Status": {"select": {"name": "Ready to Post"}}}
                )
                logger.info(f"✅ Auto-set page {page_id[:8]}... to 'Ready to Post' for immediate publishing")
            except Exception as e:
                logger.warning(f"⚠️ Failed to auto-set status to Ready: {e}")
                logger.info(f"Entry remains as 'Scheduled' - will need manual update or time-based trigger")
        
        return response
    except Exception as e:
        logger.error(f"❌ Failed to create Notion entry: {e}")
        raise

# ==============================
# MAIN WORKFLOW
# ==============================

def main():
    """Main execution workflow."""
    parser = argparse.ArgumentParser(description="Algorythmos AI Research Digest v3.0")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without writing to Notion")
    args = parser.parse_args()
    
    logger.info("=== Algorythmos AI Research Digest v3.0 ===")
    logger.info(f"Dry run mode: {args.dry_run}")
    logger.info(f"arXiv categories: {', '.join(ARXIV_CATEGORIES)}")
    
    # Ensure Notion database schema is up-to-date (self-healing)
    if NOTION_TOKEN and NOTION_DB_ID and not args.dry_run:
        ensure_notion_schema()
    
    try:
        # 1. Fetch recent arXiv papers
        papers = fetch_arxiv_papers()
        
        if not papers:
            logger.warning("No papers found from arXiv")
            return 0
        
        # 2. Get recent Notion content for duplicate detection
        notion_recent = set()
        if NOTION_TOKEN and NOTION_DB_ID:
            try:
                client = get_notion_client()
                notion_recent = get_recent_notion_content(client, NOTION_DB_ID, days=7)
                logger.info(f"📚 Found {len(notion_recent)} recent entries in Notion for duplicate checking")
            except Exception as e:
                logger.warning(f"Could not fetch Notion history for scoring: {e}")
        
        # 3. Score papers with enhanced impact filters
        scored_papers = score_papers(papers, notion_recent=notion_recent)
        
        if not scored_papers:
            logger.warning("No papers passed scoring filters")
            return 0
        
        # 4. Pick top paper
        top_paper = scored_papers[0]
        logger.info(f"🏆 Selected top paper (score={top_paper.score:.1f}):")
        logger.info(f"   📄 Title: {top_paper.title}")
        logger.info(f"   🔬 arXiv: {top_paper.arxiv_id}")
        logger.info(f"   👥 Authors: {', '.join(top_paper.authors[:3])}")
        logger.info(f"   📚 Category: {top_paper.primary_category}")
        
        # 5. Generate professional summaries
        summaries = summarize_with_openai(top_paper)
        logger.info(f"📝 Generated professional platform-specific summaries:")
        logger.info(f"   🐦 X: {summaries['char_counts']['x']}/{MAX_X_CHARS} chars")
        logger.info(f"   💼 LinkedIn: {summaries['char_counts']['linkedin']}/{MAX_LINKEDIN_CHARS} chars")
        
        # 6. Dry-run output (JSON format)
        if args.dry_run:
            output = {
                "x_text": summaries["x_text"],
                "linkedin_text": summaries["linkedin_text"],
                "char_counts": summaries["char_counts"],
                "paper": top_paper.to_dict(),
                "note": "🧪 DRY RUN: Notion write skipped"
            }
            print(json.dumps(output, ensure_ascii=False, indent=2))
            return 0
        
        # 7. Create Notion entry
        notion_create_row(top_paper, summaries)
        logger.info("=== Algorythmos AI Research Digest Completed Successfully ===")
        logger.info(f"✅ Scheduled paper {top_paper.arxiv_id} for posting")
        return 0
    
    except Exception as e:
        logger.exception("Fatal error in AI Research Digest")
        sys.exit(1)

# ==============================
# ENTRY POINT
# ==============================

if __name__ == "__main__":
    sys.exit(main())
