import os
import sys
import logging
from datetime import datetime, timezone
from notion_client import Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

def has_ready_posts():
    """
    Query Notion database for posts that are Scheduled and past their Scheduled Time.
    Returns True if any posts are ready for publication.
    """
    logger.debug("has_ready_posts() called")
    
    # Get environment variables
    notion_token = os.environ.get("NOTION_TOKEN")
    db_id = os.environ.get("NOTION_DB_ID")
    
    if not notion_token:
        logger.error("❌ NOTION_TOKEN environment variable not set")
        raise ValueError("NOTION_TOKEN is required")
    
    if not db_id:
        logger.error("❌ NOTION_DB_ID environment variable not set")
        raise ValueError("NOTION_DB_ID is required")
    
    logger.debug(f"Notion Token: {notion_token[:20]}...")
    logger.debug(f"Notion DB ID: {db_id}")
    
    # Initialize Notion client
    try:
        logger.debug("Initializing Notion client...")
        notion = Client(auth=notion_token)
        logger.info("✅ Notion client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Notion client: {e}", exc_info=True)
        raise
    
    # Calculate current time in ISO format for Notion API
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    logger.debug(f"Current time (UTC): {now}")
    
    # Build query filter
    query_filter = {
        "and": [
            {"property": "Status", "select": {"equals": "Scheduled"}},
            {"property": "Scheduled Time", "date": {"before": now}},
        ]
    }
    logger.debug(f"Query filter: {query_filter}")
    
    # Query Notion database
    try:
        logger.info(f"🔍 Querying Notion database for ready posts...")
        logger.debug(f"Database ID: {db_id}")
        logger.debug(f"Filter: Status='Scheduled' AND Scheduled Time < {now}")
        
        query = notion.databases.query(
            database_id=db_id,
            filter=query_filter,
            page_size=1,
        )
        
        results = query.get("results", [])
        result_count = len(results)
        
        logger.debug(f"Query returned {result_count} results")
        
        if result_count > 0:
            logger.info(f"✅ Found {result_count} post(s) ready for publication")
            # Log first result details at debug level
            if logger.isEnabledFor(logging.DEBUG):
                first_result = results[0]
                page_id = first_result.get("id", "unknown")
                properties = first_result.get("properties", {})
                title_prop = properties.get("Title", {})
                title_content = title_prop.get("title", [])
                title = title_content[0].get("plain_text", "Untitled") if title_content else "Untitled"
                logger.debug(f"First ready post - ID: {page_id}, Title: {title}")
            return True
        else:
            logger.info("⚠️ No posts ready for publication")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to query Notion database: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("🚀 Starting ready post check...")
    
    try:
        if has_ready_posts():
            logger.info("✅ Ready posts found — continuing to posting workflow")
            print("✅ Ready posts found — continuing to X posting.")
            sys.exit(0)
        else:
            logger.warning("⚠️ No posts ready — exiting cleanly")
            print("⚠️ No posts ready — exiting cleanly.")
            sys.exit(1)
    except Exception as e:
        logger.critical(f"❌ Fatal error during ready post check: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        sys.exit(1)
