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

def test_get_knowledge_base_not_found():
    response = client.get("/api/knowledge-bases/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge base not found"


def test_knowledge_base_invalide_uuid():
    response = client.get("/api/knowledge-bases/abc")

    assert response.status_code == 422

def teste_update_knowledge_base_partial():
    create_response = client.post(
        "/api/knowledge-bases",
        json={
            "name":"待更新知识库",
            "description":"旧描述",
            "domain":"old domain"
        }
    )

    created = create_response.json()

    update_response = client.patch(
        f"/api/knowledge-bases/{created['id']}",
        json={
            "description":"新描述"
        }
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["id"] == created["id"]
    assert updated["name"] == "待更新知识库"
    assert updated["description"] == "新描述"
    assert updated["domain"] == "old domain"

def test_update_knowledge_base_not_found():
    response = client.patch(
        "/api/knowledge-bases/00000000-0000-0000-0000-000000000000",
        json={"description": "不会成功"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge base not found"


def test_disable_knowledge_base():
    create_response = client.post(
        "api/knowledge-bases",
        json={
            "name":"待禁用知识库",
            "description":"这是一个待禁用的知识库",
            "domain":"test"
        }
    )

    created = create_response.json()

    delete_response = client.delete(f"api/knowledge-bases/{created['id']}")

    assert delete_response.status_code == 200

    deleted = delete_response.json()

    assert deleted["id"] == created["id"]
    assert deleted["status"] == "disabled"

def test_disable_knowledge_base_not_found():
    response = client.delete(
        "/api/knowledge-bases/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge base not found"
