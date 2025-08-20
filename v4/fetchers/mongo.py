# -*- coding: utf-8 -*-
"""
MongoDB fetcher for SEED Agent v4
Handles MongoDB connection and query execution
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import pymongo
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoFetcher:
    """MongoDB data fetcher with proper connection management"""
    
    def __init__(self, config):
        self.config = config
        self._clients: Dict[str, MongoClient] = {}
    
    def _get_client(self, connection_string: str) -> MongoClient:
        """Get or create MongoDB client with connection pooling"""
        if connection_string not in self._clients:
            try:
                # Configure client with sensible defaults
                self._clients[connection_string] = MongoClient(
                    connection_string,
                    serverSelectionTimeoutMS=5000,  # 5 seconds
                    connectTimeoutMS=10000,         # 10 seconds
                    socketTimeoutMS=10000,          # 10 seconds
                    maxPoolSize=5,                  # Small pool for monitoring
                    retryWrites=False,              # Don't retry writes for monitoring
                    retryReads=False                # Don't retry reads for monitoring
                )
                
                # Test connection
                self._clients[connection_string].admin.command('ping')
                logger.debug(f"MongoDB client created for {self._mask_connection_string(connection_string)}")
                
            except Exception as e:
                logger.error(f"Failed to create MongoDB client: {e}")
                raise
        
        return self._clients[connection_string]
    
    def _mask_connection_string(self, connection_string: str) -> str:
        """Mask credentials in connection string for logging"""
        if '@' in connection_string:
            parts = connection_string.split('@')
            if len(parts) >= 2:
                return f"{parts[0].split('://')[0]}://***@{parts[-1]}"
        return connection_string
    
    async def fetch_slow_queries(self, connection_string: str, min_ms: int = 100, 
                               limit: int = 10, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """Fetch slow queries from MongoDB profiler"""
        try:
            # Run in thread pool to avoid blocking
            return await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_slow_queries_sync, connection_string, min_ms, limit, timeout
            )
        except Exception as e:
            logger.error(f"Failed to fetch slow queries: {e}")
            return []
    
    def _fetch_slow_queries_sync(self, connection_string: str, min_ms: int, 
                                limit: int, timeout: float) -> List[Dict[str, Any]]:
        """Synchronous slow query fetching"""
        try:
            client = self._get_client(connection_string)
            
            # Get profiler data from system.profile collection
            # Try different databases - usually 'admin' or the main application DB
            databases_to_check = []
            
            # Get database name from connection string if specified
            if '/' in connection_string and connection_string.count('/') >= 3:
                db_from_url = connection_string.split('/')[-1].split('?')[0]
                if db_from_url and db_from_url not in ['admin', 'local', 'config']:
                    databases_to_check.append(db_from_url)
            
            # Always check common databases
            databases_to_check.extend(['admin', 'test', 'app', 'main'])
            
            slow_queries = []
            
            for db_name in databases_to_check:
                try:
                    db = client[db_name]
                    
                    # Check if profiling is enabled and system.profile exists
                    collections = db.list_collection_names()
                    if 'system.profile' not in collections:
                        continue
                    
                    # Query system.profile for slow operations
                    query = {
                        'millis': {'$gte': min_ms},
                        'ts': {'$gte': datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}  # Today only
                    }
                    
                    cursor = db['system.profile'].find(query).sort('millis', -1).limit(limit)
                    
                    for doc in cursor:
                        slow_query = {
                            'database': db_name,
                            'collection': doc.get('ns', '').split('.', 1)[-1] if '.' in doc.get('ns', '') else '',
                            'operation': doc.get('op', 'unknown'),
                            'duration_ms': doc.get('millis', 0),
                            'timestamp': doc.get('ts', datetime.utcnow()).isoformat() if isinstance(doc.get('ts'), datetime) else str(doc.get('ts', '')),
                            'command': self._format_command(doc.get('command', {})),
                            'user': doc.get('user', ''),
                            'client': doc.get('client', ''),
                            'locks': doc.get('locks', {}),
                            'query_hash': doc.get('planSummary', '') or doc.get('queryHash', ''),
                        }
                        
                        # Add query shape if available
                        if 'command' in doc and isinstance(doc['command'], dict):
                            if 'find' in doc['command']:
                                slow_query['query_type'] = 'find'
                                slow_query['collection'] = doc['command'].get('find', '')
                            elif 'aggregate' in doc['command']:
                                slow_query['query_type'] = 'aggregate'
                                slow_query['collection'] = doc['command'].get('aggregate', '')
                            elif 'update' in doc['command']:
                                slow_query['query_type'] = 'update'
                                slow_query['collection'] = doc['command'].get('update', '')
                            elif 'insert' in doc['command']:
                                slow_query['query_type'] = 'insert'
                                slow_query['collection'] = doc['command'].get('insert', '')
                            elif 'delete' in doc['command']:
                                slow_query['query_type'] = 'delete'
                                slow_query['collection'] = doc['command'].get('delete', '')
                            else:
                                slow_query['query_type'] = 'other'
                        
                        slow_queries.append(slow_query)
                        
                        if len(slow_queries) >= limit:
                            break
                    
                    if len(slow_queries) >= limit:
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not check database {db_name}: {e}")
                    continue
            
            # Sort by duration descending
            slow_queries.sort(key=lambda x: x.get('duration_ms', 0), reverse=True)
            
            logger.info(f"Found {len(slow_queries)} slow queries (min: {min_ms}ms)")
            return slow_queries[:limit]
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB connection failed: {e}")
            return []
        except PyMongoError as e:
            logger.error(f"MongoDB query failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching slow queries: {e}")
            return []
    
    def _format_command(self, command: Dict[str, Any]) -> str:
        """Format MongoDB command for display"""
        try:
            if not command:
                return "Unknown command"
            
            # Get the main operation
            main_op = None
            for op in ['find', 'aggregate', 'update', 'insert', 'delete', 'count']:
                if op in command:
                    main_op = op
                    break
            
            if not main_op:
                return str(command)[:100] + "..." if len(str(command)) > 100 else str(command)
            
            # Format based on operation type
            if main_op == 'find':
                result = f"find({command.get('find', '')})"
                if 'filter' in command and command['filter']:
                    filter_str = str(command['filter'])[:50]
                    result += f" filter: {filter_str}"
                    if len(str(command['filter'])) > 50:
                        result += "..."
                        
            elif main_op == 'aggregate':
                result = f"aggregate({command.get('aggregate', '')})"
                if 'pipeline' in command and command['pipeline']:
                    pipeline_len = len(command['pipeline'])
                    result += f" pipeline: {pipeline_len} stages"
                    
            elif main_op in ['update', 'insert', 'delete']:
                result = f"{main_op}({command.get(main_op, '')})"
                
            else:
                result = f"{main_op}: {str(command)[:50]}..."
            
            return result
            
        except Exception:
            return str(command)[:100] + "..." if len(str(command)) > 100 else str(command)
    
    async def test_connection(self, connection_string: str) -> Dict[str, Any]:
        """Test MongoDB connection and return status"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._test_connection_sync, connection_string
            )
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'latency_ms': None
            }
    
    def _test_connection_sync(self, connection_string: str) -> Dict[str, Any]:
        """Synchronous connection test"""
        import time
        
        try:
            start_time = time.time()
            client = self._get_client(connection_string)
            
            # Ping server
            result = client.admin.command('ping')
            latency_ms = (time.time() - start_time) * 1000
            
            # Get server info
            server_info = client.server_info()
            
            return {
                'connected': True,
                'server_version': server_info.get('version', 'unknown'),
                'latency_ms': round(latency_ms, 2),
                'server_info': {
                    'host': client.address[0] if client.address else 'unknown',
                    'port': client.address[1] if client.address else 'unknown',
                    'replica_set': server_info.get('replicaSet'),
                    'max_wire_version': server_info.get('maxWireVersion')
                }
            }
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'latency_ms': None
            }
    
    def close_all_connections(self):
        """Close all MongoDB connections"""
        for connection_string, client in self._clients.items():
            try:
                client.close()
                logger.debug(f"Closed MongoDB connection to {self._mask_connection_string(connection_string)}")
            except Exception as e:
                logger.warning(f"Error closing MongoDB connection: {e}")
        
        self._clients.clear()
    
    def __del__(self):
        """Cleanup connections when fetcher is destroyed"""
        try:
            self.close_all_connections()
        except Exception:
            pass