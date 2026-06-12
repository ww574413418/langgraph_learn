from fastapi.testclient import TestClient

from app.main import app


def main() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/retrieval",
        json={
            "query": "机器人无法充电怎么办",
            "mode": "parent_child",
            "strategy": "hybrid",
            "rerank_mode": "siliconflow",
            "top_k": 5,
            # 如果你想限定某个文档，就填真实 document_id。
            # "document_ids": ["..."],
            "task_type": "qa",
        },
    )

    print("status:", response.status_code)
    print(response.json())


if __name__ == "__main__":
    main()