import os
import logging
from typing import Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SupabaseClient")

# Load environment variables
load_dotenv()

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Retrieves or initializes the global Supabase client instance.
    Includes error handling for missing credentials and connection failures.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key or "your-project" in supabase_url:
        logger.warning("Supabase URL or Key is missing/unconfigured in environment variables.")
        return None

    try:
        logger.info(f"Connecting to Supabase at {supabase_url}...")
        _supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Successfully connected to Supabase.")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to connect to Supabase: {str(e)}", exc_info=True)
        return None

def check_db_health() -> bool:
    """
    Checks if Supabase database connection is active and operational.
    """
    client = get_supabase_client()
    if not client:
        return False
    try:
        # Simple health probe query
        response = client.table("projects").select("id").limit(1).execute()
        return response is not None
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return False
