import os
import logging
from typing import List, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("Database")

class Database:
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_KEY")
        self.client: Client = None
        
        if self.url and self.key:
            try:
                self.client = create_client(self.url, self.key)
                logger.info("Supabase client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
        else:
            logger.warning("SUPABASE_URL or SUPABASE_KEY not found in environment variables. Database features will be disabled.")

    def save_products(self, products: List[Dict[str, Any]], table_name: str = "zepto_assortment"):
        """
        Upserts a list of products into the specified table.
        """
        if not self.client:
            logger.warning("Supabase client not active. Skipping upload.")
            return False

        if not products:
            return True

        try:
            # Batch Insert
            response = self.client.table(table_name).insert(products).execute()
            logger.info(f"Successfully uploaded {len(products)} records to {table_name}.")
            return True
        except Exception as e:
            logger.error(f"Failed to upload data to {table_name}: {e}")
            return False

    def fetch_products(self, table_name: str = "zepto_assortment", limit: int = 1000):
        if not self.client:
            return []
            
        try:
            response = self.client.table(table_name).select("*").order("created_at", desc=True).limit(limit).execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return []
