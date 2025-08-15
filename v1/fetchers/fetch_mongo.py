# -*- coding: utf-8 -*-
"""
Обёртка для работы с MongoDB (PyMongo).
Используется плагинами для профайлера, статистики и т.п.
"""
from typing import List, Dict, Any
from pymongo import MongoClient

def aggregate(uri: str, dbname: str, collname: str, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Выполнить aggregate() и вернуть список документов.
    """
    client = MongoClient(uri)
    try:
        coll = client[dbname][collname]
        return list(coll.aggregate(pipeline))
    finally:
        client.close()