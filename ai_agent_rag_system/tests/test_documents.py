from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def create_test_knowledge_base():
    response = client.post(
        "/api/knowledge-bases",
        json={
            "name":"文档测试知识库",
            "description":"用于测试",
            "domain":"document test"
        }
    )

    assert response.status_code == 201
    return response.json()

def test_create_and_list_documents():
    knowledge_base = create_test_knowledge_base()

    payload = {
        "knowledge_base_id":knowledge_base["id"],
        "filename":"test.txt",
        "file_type":"txt",
        "file_path":"data/维护保养.txt",
        "file_hash":"document-test-hash-001"
    }

    create_response = client.post("/api/documents",json=payload)

    assert create_response.status_code == 201

    created = create_response.json()

    assert created["knowledge_base_id"] == knowledge_base["id"]
    assert created["filename"] == payload["filename"]
    assert created["file_type"] == payload["file_type"]
    assert created["file_path"] == payload["file_path"]
    assert created["file_hash"] == payload["file_hash"]
    assert created["status"] == "uploaded"
    assert created["extra_metadata"] == {}

    list_response = client.get(
        f"/api/documents?knowledge_base_id={knowledge_base['id']}"
    )

    assert list_response.status_code == 200

    items = list_response.json()

    assert any(item["id"] == created["id"] for item in items)


def test_get_document_not_found():
    response = client.get(
        "/api/documents/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


def test_create_document_knowledge_base_not_found():
    response = client.post(
        "/api/documents",
        json={
            "knowledge_base_id": "00000000-0000-0000-0000-000000000000",
            "filename": "不存在知识库.txt",
            "file_type": "txt",
            "file_path": "data/not-found.txt",
            "file_hash": "document-test-hash-not-found",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Knowledge base not found"
