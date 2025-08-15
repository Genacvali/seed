# -*- coding: utf-8 -*-
"""
Generic SQL fetcher for different database types.
Currently supports PostgreSQL.
"""
import os
from typing import Dict, List, Tuple, Optional, Any
from urllib.parse import urlparse

def fetch_sql(db_type: str, connection_config: Optional[Dict], query: str, params: Dict) -> Optional[List[Tuple]]:
    """
    Execute SQL query and return results.
    
    Args:
        db_type: Database type ('postgres', 'mysql', etc.)
        connection_config: Connection configuration (currently unused, using params['dsn'])
        query: SQL query to execute
        params: Parameters including 'dsn' connection string
        
    Returns:
        List of tuples with query results or None on error
    """
    if db_type.lower() != 'postgres':
        raise NotImplementedError(f"Database type '{db_type}' not supported yet")
    
    dsn = params.get('dsn')
    if not dsn:
        raise ValueError("DSN connection string required in params")
    
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        raise ImportError("psycopg2 required for PostgreSQL connections. Install with: pip install psycopg2-binary")
    
    try:
        # Parse DSN to add SSL settings if needed
        parsed = urlparse(dsn)
        
        # Connect to database
        conn = psycopg2.connect(dsn)
        conn.set_session(autocommit=True)
        
        with conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            
        conn.close()
        return rows
        
    except psycopg2.Error as e:
        print(f"PostgreSQL error: {e}")
        return None
    except Exception as e:
        print(f"Database connection error: {e}")
        return None