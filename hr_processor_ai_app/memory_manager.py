import sys
import asyncio



import os
import asyncio
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from django.conf import settings
from typing import Optional
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Centralized Postgres config
LANGGRAPH_POSTGRES = {
    'DATABASE': os.getenv('PSQL_DATABASE', 'hr_processor_ai'),
    'USERNAME': os.getenv('PSQL_USERNAME', 'postgres'),
    'PASSWORD': os.getenv('PSQL_PASSWORD', ''),
    'HOST': os.getenv('PSQL_HOST', 'localhost'),
    'PORT': os.getenv('PSQL_PORT', '5432'),
    'SSLMODE': os.getenv('PSQL_SSLMODE', 'disable'),
}

class MemoryManager:
    """Manages PostgreSQL memory for LangGraph agents"""
    
    def __init__(self):
        self.pool = None
        self.memory = None
        self._setup_done = False
    
    async def initialize(self):
        """Initialize PostgreSQL connection pool and memory"""
        try:
            # Create connection string
            conninfo = (
                f"postgres://{LANGGRAPH_POSTGRES['USERNAME']}:"
                f"{LANGGRAPH_POSTGRES['PASSWORD']}@"
                f"{LANGGRAPH_POSTGRES['HOST']}:"
                f"{LANGGRAPH_POSTGRES['PORT']}/"
                f"{LANGGRAPH_POSTGRES['DATABASE']}"
                f"?sslmode={LANGGRAPH_POSTGRES['SSLMODE']}"
            )
            
            # Create async connection pool
            self.pool = AsyncConnectionPool(
                conninfo=conninfo,
                max_size=10,
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row,
                }
            )
            
            # Get connection and setup memory
            async with self.pool.connection() as conn:
                self.memory = AsyncPostgresSaver(conn)
                
                # Setup tables on first run (only run once)
                if not self._setup_done:
                    await self.memory.setup()
                    self._setup_done = True
                    logger.info("✅ LangGraph PostgreSQL memory initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize memory: {e}")
            return False
    
    async def get_memory(self):
        """Get memory instance with fresh connection"""
        if not self.pool:
            await self.initialize()
        
        # Get a new connection for this request
        conn = await self.pool.getconn()
        return AsyncPostgresSaver(conn), conn
    
    async def close(self):
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

# Global memory manager instance
memory_manager = MemoryManager()