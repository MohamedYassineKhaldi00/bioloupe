from app.main import create_app
from fastapi.testclient import TestClient
app = create_app()
client = TestClient(app)
resp = client.post('/api/v1/materials/upload/mat-1/complete', json={'checksum':'abc','parts':[]})
print('status', resp.status_code)
try:
    print('json', resp.json())
except Exception:
    print('text', resp.text)
