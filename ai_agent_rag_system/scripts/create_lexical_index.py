from opensearchpy import OpenSearch

from app.core.config import settings
from app.rag.lexical_index import CHUNK_INDEX_SETTINGS


def main() -> None:
    """
    创建 OpenSearch chunk 索引。

    这个脚本只负责 index schema：
    - analyzer
    - mappings
    - BM25 similarity

    不负责写入 chunk 数据。
    """
    client = OpenSearch(hosts=[settings.opensearch_url])
    index_name = settings.opensearch_chunks_index

    if client.indices.exists(index=index_name):
        print(f"index exists: {index_name}")
        return

    client.indices.create(
        index=index_name,
        body=CHUNK_INDEX_SETTINGS,
    )

    print(f"created index: {index_name}")


if __name__ == "__main__":
    main()