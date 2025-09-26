import asyncio
import sqlite3
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import uvicorn

app = FastAPI()

# CORS để Streamlit kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kết nối SQLite
conn = sqlite3.connect('student_management.db', check_same_thread=False)
cursor = conn.cursor()

# Danh sách client đang kết nối (hỗ trợ nhiều client per session)
connected_clients = {}

@app.get("/")
async def root():
    return {"message": "Chat WebSocket Server"}

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    await websocket.accept()
    # Lưu client vào danh sách
    if session_id not in connected_clients:
        connected_clients[session_id] = []
    connected_clients[session_id].append(websocket)

    try:
        while True:
            # Nhận tin nhắn từ client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Lưu tin nhắn vào SQLite
            cursor.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    message_data["role"],
                    message_data["content"],
                    message_data["timestamp"],
                    1 if message_data["role"] in ["assistant", "teacher"] else 0
                )
            )
            conn.commit()

            # Gửi tin nhắn tới tất cả client trong session (trừ người gửi)
            for client in connected_clients.get(session_id, []):
                if client != websocket and client.client_state == "connected":
                    await client.send_text(json.dumps({
                        "session_id": session_id,
                        "role": message_data["role"],
                        "content": message_data["content"],
                        "timestamp": message_data["timestamp"]
                    }))

    except WebSocketDisconnect:
        # Xóa client khỏi danh sách khi ngắt kết nối
        connected_clients[session_id].remove(websocket)
        if not connected_clients[session_id]:
            del connected_clients[session_id]

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)