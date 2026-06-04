# app/rag/lexical_index.py

CHUNK_INDEX_SETTINGS = {
    "settings": {
        "analysis": {
            "analyzer": {
                "rag_zh_analyzer": {
                    "type": "cjk"
                }
            }
        }
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "document_id": {"type": "keyword"},
            "parent_id": {"type": "keyword"},
            "chunk_type": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "content": {
                "type": "text",
                "analyzer": "rag_zh_analyzer",
                "search_analyzer": "rag_zh_analyzer",
                "similarity": "BM25",
            },
            "filename": {
                "type": "text",
                "analyzer": "rag_zh_analyzer",
                "fields": {
                    "keyword": {"type": "keyword"}
                },
            },
            "section_title": {
                "type": "text",
                "analyzer": "rag_zh_analyzer",
            },
            "content_hash": {"type": "keyword"},
            "token_count": {"type": "integer"},
            "char_count": {"type": "integer"},
            "start_char": {"type": "integer"},
            "end_char": {"type": "integer"},
            "extra_metadata": {"type": "object", "enabled": False},
        }
    },
}