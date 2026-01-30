from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import y_py as Y

from src.app.websocket.handlers.crdt import CRDTHandlers
from src.app.websocket.services.yjs_service import YjsService


@pytest.fixture
async def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    return redis


@pytest.fixture
async def yjs_service(mock_redis):
    """Create YjsService instance."""
    return YjsService(mock_redis)


@pytest.fixture
async def mock_sio():
    """Mock Socket.IO server."""
    sio = MagicMock()
    sio.get_session = AsyncMock()
    sio.emit = AsyncMock()
    sio.enter_room = AsyncMock()
    sio.leave_room = AsyncMock()
    return sio


@pytest.fixture
async def crdt_handlers(mock_sio, yjs_service):
    """Create CRDTHandlers instance."""
    return CRDTHandlers(mock_sio, yjs_service)


@pytest.mark.asyncio
async def test_yjs_service_create_document(yjs_service):
    """Test creating new Y.js document."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)

    assert doc is not None
    assert material_id in yjs_service.documents
    assert material_id in yjs_service._last_activity


@pytest.mark.asyncio
async def test_yjs_service_restore_document(mock_redis):
    """Test restoring Y.js document from Redis."""
    material_id = str(uuid4())

    doc = Y.YDoc()
    text = doc.get_text("content")
    with doc.begin_transaction() as txn:
        text.extend(txn, "Hello World")

    state = Y.encode_state_as_update(doc)
    mock_redis.get = AsyncMock(return_value=state.hex())

    service = YjsService(mock_redis)
    restored_doc = await service.get_or_create_document(material_id)

    assert restored_doc is not None
    restored_text = restored_doc.get_text("content")
    assert str(restored_text) == "Hello World"


@pytest.mark.asyncio
async def test_yjs_service_save_document(yjs_service, mock_redis):
    """Test saving Y.js document to Redis."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)
    text = doc.get_text("content")
    with doc.begin_transaction() as txn:
        text.extend(txn, "Test content")

    await yjs_service.save_document_state(material_id)

    mock_redis.set.assert_called()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == f"ydoc:{material_id}"


@pytest.mark.asyncio
async def test_yjs_service_apply_update(yjs_service):
    """Test applying update to Y.js document."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)

    client_doc = Y.YDoc()
    client_text = client_doc.get_text("content")
    with client_doc.begin_transaction() as txn:
        client_text.extend(txn, "Client update")

    update = Y.encode_state_as_update(client_doc)

    state_vector = await yjs_service.apply_update(material_id, update)

    assert state_vector is not None
    server_text = doc.get_text("content")
    assert str(server_text) == "Client update"


@pytest.mark.asyncio
async def test_yjs_service_concurrent_updates(yjs_service):
    """Test concurrent updates merge correctly (CRDT)."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)

    client1_doc = Y.YDoc()
    client1_text = client1_doc.get_text("content")
    with client1_doc.begin_transaction() as txn:
        client1_text.extend(txn, "Client 1")

    client2_doc = Y.YDoc()
    client2_text = client2_doc.get_text("content")
    with client2_doc.begin_transaction() as txn:
        client2_text.extend(txn, "Client 2")

    update1 = Y.encode_state_as_update(client1_doc)
    update2 = Y.encode_state_as_update(client2_doc)

    await yjs_service.apply_update(material_id, update1)
    await yjs_service.apply_update(material_id, update2)

    server_text = doc.get_text("content")
    content = str(server_text)

    assert "Client 1" in content or "Client 2" in content


@pytest.mark.asyncio
async def test_yjs_service_get_missing_updates(yjs_service):
    """Test getting missing updates for client."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)
    text = doc.get_text("content")
    with doc.begin_transaction() as txn:
        text.extend(txn, "Server content")

    client_doc = Y.YDoc()
    client_state_vector = Y.encode_state_vector(client_doc)

    missing_updates = await yjs_service.get_missing_updates(
        material_id,
        client_state_vector
    )

    assert missing_updates is not None
    assert len(missing_updates) > 0

    Y.apply_update(client_doc, missing_updates)
    client_text = client_doc.get_text("content")
    assert str(client_text) == "Server content"


@pytest.mark.asyncio
async def test_yjs_service_cleanup_document(yjs_service, mock_redis):
    """Test cleaning up inactive document."""
    material_id = str(uuid4())

    await yjs_service.get_or_create_document(material_id)
    assert material_id in yjs_service.documents

    await yjs_service.cleanup_document(material_id)

    assert material_id not in yjs_service.documents
    mock_redis.set.assert_called()


@pytest.mark.asyncio
async def test_yjs_service_cleanup_inactive_documents(yjs_service):
    """Test automatic cleanup of inactive documents."""
    material_id = str(uuid4())

    await yjs_service.get_or_create_document(material_id)

    import datetime
    old_time = datetime.datetime.now(
        datetime.timezone.utc
    ) - datetime.timedelta(seconds=700)
    yjs_service._last_activity[material_id] = old_time

    removed = await yjs_service.cleanup_inactive_documents(600)

    assert removed == 1
    assert material_id not in yjs_service.documents


@pytest.mark.asyncio
async def test_crdt_handlers_sync_step1(crdt_handlers, mock_sio):
    """Test Y.js sync step 1 handler."""
    material_id = str(uuid4())
    user_id = str(uuid4())
    sid = "test-sid"

    mock_sio.get_session.return_value = {
        "authenticated": True,
        "user_id": user_id
    }

    client_doc = Y.YDoc()
    state_vector = Y.encode_state_vector(client_doc)

    data = {
        "material_id": material_id,
        "state_vector": state_vector.hex()
    }

    await crdt_handlers.handle_yjs_sync_step1(sid, data)

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "yjs:sync_step2"
    assert "update" in call_args[0][1]


@pytest.mark.asyncio
async def test_crdt_handlers_update(crdt_handlers, mock_sio, yjs_service):
    """Test Y.js update handler."""
    material_id = str(uuid4())
    user_id = str(uuid4())
    sid = "test-sid"

    mock_sio.get_session.return_value = {
        "authenticated": True,
        "user_id": user_id
    }

    client_doc = Y.YDoc()
    text = client_doc.get_text("content")
    with client_doc.begin_transaction() as txn:
        text.extend(txn, "New content")

    update = Y.encode_state_as_update(client_doc)

    data = {
        "material_id": material_id,
        "update": update.hex()
    }

    await crdt_handlers.handle_yjs_update(sid, data)

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "yjs:update"
    assert call_args[1]["room"] == f"material:{material_id}"
    assert call_args[1]["skip_sid"] == sid


@pytest.mark.asyncio
async def test_crdt_handlers_awareness_update(
    crdt_handlers,
    mock_sio
):
    """Test Y.js awareness update handler."""
    material_id = str(uuid4())
    user_id = str(uuid4())
    sid = "test-sid"

    mock_sio.get_session.return_value = {
        "authenticated": True,
        "user_id": user_id
    }

    data = {
        "material_id": material_id,
        "awareness_update": "deadbeef"
    }

    await crdt_handlers.handle_yjs_awareness_update(sid, data)

    mock_sio.emit.assert_called_once()
    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "yjs:awareness_update"
    assert call_args[0][1]["user_id"] == user_id


@pytest.mark.asyncio
async def test_crdt_handlers_material_subscribe(
    crdt_handlers,
    mock_sio
):
    """Test subscribing to material."""
    material_id = str(uuid4())
    user_id = str(uuid4())
    sid = "test-sid"

    mock_sio.get_session.return_value = {
        "authenticated": True,
        "user_id": user_id
    }

    data = {"material_id": material_id}

    await crdt_handlers.handle_material_subscribe(sid, data)

    mock_sio.enter_room.assert_called_once_with(
        sid,
        f"material:{material_id}"
    )
    mock_sio.emit.assert_called_once()


@pytest.mark.asyncio
async def test_crdt_handlers_material_unsubscribe(
    crdt_handlers,
    mock_sio
):
    """Test unsubscribing from material."""
    material_id = str(uuid4())
    sid = "test-sid"

    data = {"material_id": material_id}

    await crdt_handlers.handle_material_unsubscribe(sid, data)

    mock_sio.leave_room.assert_called_once_with(
        sid,
        f"material:{material_id}"
    )


@pytest.mark.asyncio
async def test_crdt_handlers_auth_required(crdt_handlers, mock_sio):
    """Test authentication is required."""
    material_id = str(uuid4())
    sid = "test-sid"

    mock_sio.get_session.return_value = None

    data = {
        "material_id": material_id,
        "state_vector": "00"
    }

    await crdt_handlers.handle_yjs_sync_step1(sid, data)

    call_args = mock_sio.emit.call_args
    assert call_args[0][0] == "error"
    assert "AUTH_REQUIRED" in call_args[0][1]["code"]


@pytest.mark.asyncio
async def test_yjs_document_size_tracking(yjs_service):
    """Test tracking document size."""
    material_id = str(uuid4())

    doc = await yjs_service.get_or_create_document(material_id)
    text = doc.get_text("content")
    with doc.begin_transaction() as txn:
        text.extend(txn, "A" * 1000)

    size = await yjs_service.get_document_size(material_id)

    assert size > 0


@pytest.mark.asyncio
async def test_yjs_save_all_documents(yjs_service, mock_redis):
    """Test saving all active documents."""
    material_ids = [str(uuid4()) for _ in range(3)]

    for material_id in material_ids:
        await yjs_service.get_or_create_document(material_id)

    count = await yjs_service.save_all_documents()

    assert count == 3
    assert mock_redis.set.call_count >= 3
