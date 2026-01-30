"""
Example usage of BioLoupe WebSocket infrastructure.

This demonstrates connecting to the WebSocket server,
authenticating, joining sessions, and handling real-time events.
"""
import asyncio
import json
from datetime import datetime

import socketio


async def main():
    # Create Socket.io client
    sio = socketio.AsyncClient(
        logger=True,
        engineio_logger=False
    )

    # JWT token (replace with actual token from login)
    jwt_token = "your-jwt-token-here"

    # Event handlers
    @sio.event
    async def connect():
        print("✓ Connected to WebSocket server")
        print(f"  Session ID: {sio.sid}")

    @sio.event
    async def connect_error(data):
        print(f"✗ Connection failed: {data}")

    @sio.event
    async def disconnect():
        print("✓ Disconnected from server")

    @sio.event
    async def user_joined(data):
        print(f"→ User joined: {data['full_name']}")
        print(f"  Session: {data['session_id']}")

    @sio.event
    async def user_left(data):
        print(f"← User left: {data['user_id']}")

    @sio.event
    async def user_disconnected(data):
        print(f"⚠ User disconnected: {data['user_id']}")

    @sio.event
    async def cursor_position(data):
        print(f"🖱 Cursor: {data['user_id']} at ({data['x']}, {data['y']})")

    @sio.event
    async def material_added(data):
        print(f"📄 Material added: {data['title']}")
        print(f"  Type: {data['material_type']}")

    @sio.event
    async def presence_update(data):
        print(f"👤 Presence: {data['user_id']} is {data['status']}")

    @sio.event
    async def error(data):
        print(f"⚠ Error: {data['message']}")
        if 'code' in data:
            print(f"  Code: {data['code']}")

    # Connect with authentication
    try:
        await sio.connect(
            'http://localhost:8000/ws',
            socketio_path='/ws/socket.io',
            auth={'token': jwt_token}
        )
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    # Join a session
    session_id = "your-session-id-here"

    response = await sio.call(
        'join_session',
        {'session_id': session_id}
    )

    if response.get('success'):
        print(f"✓ Joined session: {session_id}")
        print(f"  Participants: {len(response.get('participants', []))}")
        for participant in response.get('participants', []):
            print(f"    - {participant['full_name']} ({participant['status']})")
    else:
        print(f"✗ Failed to join: {response.get('error')}")
        await sio.disconnect()
        return

    # Simulate some activity
    print("\n--- Simulating activity ---\n")

    # Send cursor position
    await sio.emit('cursor_position', {
        'session_id': session_id,
        'user_id': 'current-user-id',
        'x': 150.5,
        'y': 200.3,
        'element_id': 'canvas-1'
    })
    print("Sent cursor position")

    # Send heartbeat
    heartbeat_data = {
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    heartbeat_response = await sio.call('heartbeat', heartbeat_data)
    if heartbeat_response.get('success'):
        print("✓ Heartbeat acknowledged")

    # Keep connection alive
    print("\nConnection active. Press Ctrl+C to disconnect...\n")

    # Heartbeat loop
    try:
        while True:
            await asyncio.sleep(30)
            heartbeat_response = await sio.call('heartbeat', {
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            })
            if heartbeat_response.get('success'):
                print("♥ Heartbeat")
    except KeyboardInterrupt:
        print("\n\nDisconnecting...")

    # Leave session
    leave_response = await sio.call(
        'leave_session',
        {'session_id': session_id}
    )

    if leave_response.get('success'):
        print("✓ Left session")

    # Disconnect
    await sio.disconnect()
    print("✓ Disconnected")


async def namespace_example():
    """Example using Socket.io namespaces."""

    jwt_token = "your-jwt-token-here"
    session_id = "your-session-id-here"

    # Connect to session namespace
    sio_session = socketio.AsyncClient()

    @sio_session.event
    async def connect():
        print("Connected to /sessions namespace")

    @sio_session.event
    async def material_added(data):
        print(f"Material added via namespace: {data}")

    await sio_session.connect(
        'http://localhost:8000/sessions',
        socketio_path='/ws/socket.io',
        auth={'token': jwt_token}
    )

    # Join session
    await sio_session.emit('join_session', {'session_id': session_id})

    # Emit material added
    await sio_session.emit('material_added', {
        'session_id': session_id,
        'material_id': 'material-uuid',
        'user_id': 'user-uuid',
        'material_type': 'paper',
        'title': 'New Research Paper'
    })

    await asyncio.sleep(2)
    await sio_session.disconnect()


async def presence_example():
    """Example using presence namespace."""

    jwt_token = "your-jwt-token-here"
    session_id = "your-session-id-here"

    sio_presence = socketio.AsyncClient()

    @sio_presence.event
    async def cursor_position(data):
        print(f"Cursor from {data['user_id']}: ({data['x']}, {data['y']})")

    await sio_presence.connect(
        'http://localhost:8000/presence',
        socketio_path='/ws/socket.io',
        auth={'token': jwt_token}
    )

    # Send cursor updates
    for i in range(5):
        await sio_presence.emit('cursor_position', {
            'session_id': session_id,
            'user_id': 'user-uuid',
            'x': 100 + i * 10,
            'y': 200 + i * 10
        })
        await asyncio.sleep(0.5)

    await sio_presence.disconnect()


if __name__ == '__main__':
    print("BioLoupe WebSocket Example\n")
    print("=" * 50)
    print()

    # Run main example
    asyncio.run(main())

    # Uncomment to run namespace examples
    # asyncio.run(namespace_example())
    # asyncio.run(presence_example())
