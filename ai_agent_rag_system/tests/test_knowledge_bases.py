from fastapi.testclient import  TestClient
from app.main import app

client  = TestClient(app)

def test_create_and_list_knowledge_base():
    payload = {
        "name":"测试知识库",
        "description":"这是一个测试知识库",
        "domain":"test"
    }

    create_response = client.post("/api/knowledge-bases",json=payload)

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["name"] == payload["name"]
    assert created["description"] == payload["description"]
    assert created["domain"] == payload["domain"]
    assert created["status"] == "active"
    assert "id" in created
    assert "created_at" in created

    list_response = client.get("/api/knowledge-bases")

    assert list_response.status_code == 200

    items = list_response.json()
    assert any(item["id"] == created["id"] for item in items)