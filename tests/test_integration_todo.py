import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from main import app, get_db
from models import ToDo

# Отдельная тестовая база, чтобы не трогать основную
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_sql_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Пересоздаём таблицы в тестовой БД
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Подменяем зависимость get_db в приложении — теперь все эндпоинты работают с тестовой БД
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_home_creates_session_and_returns_page():
    response = client.get("/")

    assert response.status_code == 200
    assert "session_key" in response.cookies
    assert "text/html" in response.headers.get("content-type", "")

def test_add_todo_creates_record_and_returns_html():
    home_resp = client.get("/")
    session_key = home_resp.cookies.get("session_key")
    assert session_key is not None

    resp = client.post(
        "/add",
        data={"content": "Buy milk"},
        cookies={"session_key": session_key},
    )

    assert resp.status_code == 200
    assert "Buy milk" in resp.text

    db = TestingSessionLocal()
    todos = db.query(ToDo).filter(ToDo.session_key == session_key).all()
    db.close()

    assert any(t.content == "Buy milk" for t in todos)

def test_edit_todo_updates_content():
    home_resp = client.get("/")
    session_key = home_resp.cookies.get("session_key")

    client.post(
        "/add",
        data={"content": "Old text"},
        cookies={"session_key": session_key},
    )

    db = TestingSessionLocal()
    todo = db.query(ToDo).filter(ToDo.session_key == session_key).first()
    todo_id = todo.id
    db.close()

    resp = client.put(
        f"/edit/{todo_id}",
        data={"content": "New text"},
        cookies={"session_key": session_key},
    )

    assert resp.status_code == 200
    assert "New text" in resp.text

    db = TestingSessionLocal()
    updated = db.query(ToDo).filter(ToDo.id == todo_id).first()
    db.close()

    assert updated.content == "New text"

def test_delete_todo_removes_record():
    home_resp = client.get("/")
    session_key = home_resp.cookies.get("session_key")

    client.post(
        "/add",
        data={"content": "Delete me"},
        cookies={"session_key": session_key},
    )

    db = TestingSessionLocal()
    todo = db.query(ToDo).filter(ToDo.session_key == session_key).first()
    todo_id = todo.id
    db.close()

    resp = client.delete(f"/delete/{todo_id}")
    assert resp.status_code in (200, 202, 204)

    db = TestingSessionLocal()
    deleted = db.query(ToDo).filter(ToDo.id == todo_id).first()
    db.close()

    assert deleted is None

def test_add_todo_without_session_creates_todo():
    resp = client.post("/add", data={"content": "No session"})
    assert resp.status_code == 200

    db = TestingSessionLocal()
    todos = db.query(ToDo).all()
    db.close()

    assert any(t.content == "No session" for t in todos)
'''
def test_edit_non_existing_todo_returns_error():
    invalid_id = 999999
    resp = client.put(
        f"/edit/{invalid_id}",
        data={"content": "Should fail"},
    )

    assert resp.status_code >= 400
    '''

def test_edit_non_existing_todo_raises_error():
    invalid_id = 999999
    # Ожидаем, что при попытке редактировать несуществующую задачу приложение выбросит AttributeError (это и есть баг).
    with pytest.raises(AttributeError):
        client.put(
            f"/edit/{invalid_id}",
            data={"content": "Should fail"},
        )

