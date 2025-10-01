import asyncio
import psycopg  # Changed from psycopg2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
import json
from fastapi.responses import StreamingResponse
from fastapi.websockets import WebSocketState
import uvicorn
from datetime import datetime, timedelta, timezone
from groq import Groq
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from jose import JWTError, jwt
import secrets

load_dotenv()

# JWT Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Database Configuration
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

try:
    conn = psycopg.connect(  # Changed from psycopg2.connect
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor()
    print("Connected to PostgreSQL database")
except Exception as e:
    print(f"Failed to connect to database: {str(e)}")
    raise

# Initialize Groq client
try:
    client = Groq(api_key=os.environ.get("OPENAI_API_KEY"))
    test_response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "test"}],
        max_tokens=10
    )
    print("Groq client initialized successfully")
except Exception as e:
    print(f"Failed to initialize Groq client: {str(e)}")
    client = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE,
    name TEXT,
    class TEXT,
    gvcn TEXT,
    password TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS chat_sessions (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES students(id),
    title TEXT,
    created_at TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id),
    role TEXT,
    content TEXT,
    timestamp TEXT,
    read_by_teacher INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    user_type TEXT,
    token TEXT UNIQUE,
    expires_at TEXT
)
""")
cursor.execute("INSERT INTO teachers (username, password) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                ("teacher", "123456"))
conn.commit()

connected_clients = {}  # {session_id: {user_id: [websocket]}}
teacher_connections = {}

class Message(BaseModel):
    session_id: int
    role: str
    content: str
    timestamp: str

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: int
    ai_enabled: bool

class StudentRegister(BaseModel):
    username: str
    name: str
    class_name: str
    gvcn: str
    password: str

class StudentLogin(BaseModel):
    username: str
    password: str

class TeacherLogin(BaseModel):
    username: str
    password: str

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire.isoformat()

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        user_type = payload.get("type")
        if user_id is None or user_type is None:
            print("Token validation failed: Missing user_id or user_type")
            return None
        user_id = int(user_id)
        cursor.execute("SELECT token, expires_at FROM tokens WHERE token = %s AND user_id = %s AND user_type = %s",
                        (token, user_id, user_type))
        result = cursor.fetchone()
        if not result:
            print(f"Token not found in database: token={token}, user_id={user_id}, user_type={user_type}")
            return None
        if datetime.fromisoformat(result[1]) < datetime.now(timezone.utc):
            print(f"Token expired: expires_at={result[1]}")
            return None
        print(f"Token validated: user_id={user_id}, user_type={user_type}")
        return {"user_id": user_id, "user_type": user_type}
    except JWTError as e:
        print(f"JWTError: {str(e)}")
        return None

@app.get("/")
async def root():
    return {"message": "Chat Server"}

@app.get("/students")
async def get_students(token: str):
    user = verify_token(token)
    if not user or user["user_type"] != "teacher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT id, username, name, class, gvcn FROM students")
    students = cursor.fetchall()
    return [{"id": s[0], "username": s[1], "name": s[2], "class": s[3], "gvcn": s[4]} for s in students]

@app.post("/student_register")
async def student_register(student: StudentRegister):
    cursor.execute("SELECT username FROM students WHERE username = %s", (student.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Số điện thoại đã được đăng ký")
    cursor.execute(
        "INSERT INTO students (username, name, class, gvcn, password) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (student.username, student.name, student.class_name, student.gvcn, student.password)
    )
    student_id = cursor.fetchone()[0]
    conn.commit()
    return {"id": student_id}

@app.post("/student_login")
async def student_login(student: StudentLogin):
    cursor.execute("SELECT id FROM students WHERE username = %s AND password = %s",
                    (student.username, student.password))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
        token, expires_at = create_access_token({"sub": str(user_id), "type": "student"})
        cursor.execute("INSERT INTO tokens (user_id, user_type, token, expires_at) VALUES (%s, %s, %s, %s)",
                        (user_id, "student", token, expires_at))
        conn.commit()
        return {"id": user_id, "token": token}
    raise HTTPException(status_code=401, detail="Sai tài khoản hoặc mật khẩu")

@app.post("/teacher_login")
async def teacher_login(teacher: TeacherLogin):
    cursor.execute("SELECT id FROM teachers WHERE username = %s AND password = %s",
                    (teacher.username, teacher.password))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
        token, expires_at = create_access_token({"sub": str(user_id), "type": "teacher"})
        cursor.execute("INSERT INTO tokens (user_id, user_type, token, expires_at) VALUES (%s, %s, %s, %s)",
                        (user_id, "teacher", token, expires_at))
        conn.commit()
        return {"id": user_id, "token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/teacher/{teacher_id}")
async def get_teacher(teacher_id: int, token: str):
    user = verify_token(token)
    if not user or (user["user_type"] == "teacher" and user["user_id"] != teacher_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT id, username FROM teachers WHERE id = %s", (teacher_id,))
    teacher = cursor.fetchone()
    if teacher:
        return {"id": teacher[0], "username": teacher[1]}
    raise HTTPException(status_code=404, detail="Teacher not found")

@app.websocket("/ws/teacher/{teacher_id}/{token}")
async def teacher_websocket_endpoint(websocket: WebSocket, teacher_id: int, token: str):
    user = verify_token(token)
    if not user or user["user_type"] != "teacher" or user["user_id"] != teacher_id:
        await websocket.close(code=1008)
        print(f"WebSocket connection rejected: Invalid token or unauthorized for teacher_id {teacher_id}")
        return

    await websocket.accept()
    print(f"WebSocket accepted for teacher_id: {teacher_id}")

    if teacher_id not in teacher_connections:
        teacher_connections[teacher_id] = []
    teacher_connections[teacher_id].append(websocket)

    try:
        async def keep_alive():
            while websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    print(f"Sent ping for teacher_id: {teacher_id}")
                    await asyncio.sleep(30)
                except Exception as e:
                    print(f"Ping error for teacher_id {teacher_id}: {str(e)}")
                    break

        asyncio.create_task(keep_alive())

        while True:
            await websocket.receive_text()
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected for teacher_id {teacher_id}, code: {e.code}, reason: {e.reason}")
        if teacher_id in teacher_connections:
            if websocket in teacher_connections[teacher_id]:
                teacher_connections[teacher_id].remove(websocket)
            if not teacher_connections[teacher_id]:
                del teacher_connections[teacher_id]
    except Exception as e:
        print(f"Unexpected error in WebSocket for teacher_id {teacher_id}: {str(e)}")
    finally:
        if teacher_id in teacher_connections:
            if websocket in teacher_connections[teacher_id]:
                teacher_connections[teacher_id].remove(websocket)
            if not teacher_connections[teacher_id]:
                del teacher_connections[teacher_id]

@app.get("/sessions/{student_id}")
async def get_sessions(student_id: int, token: str):
    user = verify_token(token)
    if not user or (user["user_type"] == "student" and user["user_id"] != student_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT id, title, created_at FROM chat_sessions WHERE student_id = %s ORDER BY created_at DESC",
                    (student_id,))
    sessions = cursor.fetchall()
    return [{"id": s[0], "title": s[1], "created_at": s[2]} for s in sessions]

@app.post("/sessions")
async def create_session(session: dict = Body(...), token: str = Body(...)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor.execute("INSERT INTO chat_sessions (student_id, title, created_at) VALUES (%s, %s, %s) RETURNING id",
                    (session["student_id"], session["title"], timestamp))
    session_id = cursor.fetchone()[0]
    conn.commit()
    return {"id": session_id}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: int, token: str = Query(...)):
    user = verify_token(token)
    if not user or user["user_type"] != "student":
        raise HTTPException(status_code=401, detail="Unauthorized")

    cursor.execute("SELECT student_id FROM chat_sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()
    if not session or session[0] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Forbidden: You can only delete your own sessions")

    cursor.execute("DELETE FROM conversations WHERE session_id = %s", (session_id,))
    cursor.execute("DELETE FROM chat_sessions WHERE id = %s", (session_id,))
    conn.commit()

    if session_id in connected_clients:
        for user_id, clients in list(connected_clients[session_id].items()):
            for client_ws in clients[:]:
                try:
                    await client_ws.close(code=1000, reason="Session deleted")
                    clients.remove(client_ws)
                except Exception as e:
                    print(f"Error closing WebSocket for session_id {session_id}, user_id {user_id}: {str(e)}")
            if not clients:
                del connected_clients[session_id][user_id]
        if not connected_clients[session_id]:
            del connected_clients[session_id]

    return {"status": "ok"}

@app.get("/conversations/{session_id}")
async def get_conversations(session_id: int, token: str):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT role, content, timestamp FROM conversations WHERE session_id = %s ORDER BY timestamp",
                    (session_id,))
    messages = cursor.fetchall()
    return [{"role": m[0], "content": m[1], "timestamp": m[2]} for m in messages]

async def broadcast_message_to_teachers(student_id: int, session_id: int, last_message_time: str):
    print(f"Broadcasting new message to teachers: student_id={student_id}, session_id={session_id}, last_message_time={last_message_time}")
    for teacher_id, clients in list(teacher_connections.items()):
        for client_ws in clients[:]:
            if client_ws.client_state == WebSocketState.CONNECTED:
                for attempt in range(3):
                    try:
                        await client_ws.send_text(
                            json.dumps(
                                {
                                    "type": "new_message",
                                    "studentId": student_id,
                                    "sessionId": session_id,
                                    "lastMessageTime": last_message_time,
                                },
                                ensure_ascii=False,
                            )
                        )
                        print(f"Sent new message to teacher_id: {teacher_id} for student_id: {student_id}")
                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed to send message to teacher_id {teacher_id}: {str(e)}")
                        if attempt == 2:
                            print(f"Removing disconnected client for teacher_id {teacher_id}")
                            clients.remove(client_ws)
            else:
                print(f"Client not connected for teacher_id {teacher_id}")
                clients.remove(client_ws)
        teacher_connections[teacher_id] = [ws for ws in clients if ws.client_state == WebSocketState.CONNECTED]
        if not teacher_connections[teacher_id]:
            del teacher_connections[teacher_id]

async def broadcast_message_to_clients(session_id: int, broadcast_message: dict):
    if session_id not in connected_clients:
        print(f"No connected clients for session_id {session_id}")
        return
    print(f"Preparing to broadcast message: {broadcast_message}")
    await asyncio.sleep(0.1)

    cursor.execute("SELECT student_id FROM chat_sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()
    if not session:
        print(f"Session {session_id} not found")
        return
    student_id = session[0]

    for user_id, clients in list(connected_clients[session_id].items()):
        if user_id != student_id and broadcast_message["role"] != "teacher":
            print(f"Skipping broadcast to user_id {user_id} for session_id {session_id} (not student or teacher)")
            continue
        for client_ws in clients[:]:
            if client_ws.client_state == WebSocketState.CONNECTED:
                for attempt in range(3):
                    try:
                        await client_ws.send_text(json.dumps(broadcast_message, ensure_ascii=False))
                        print(f"Sent message to WebSocket for session_id: {session_id}, user_id: {user_id}")
                        break
                    except Exception as e:
                        print(f"Attempt {attempt + 1} failed to send message to user_id {user_id} for session_id {session_id}: {str(e)}")
                        if attempt == 2:
                            print(f"Removing disconnected client for user_id {user_id}, session_id {session_id}")
                            clients.remove(client_ws)
            else:
                print(f"Client not connected for user_id {user_id}, session_id {session_id}")
                clients.remove(client_ws)
        connected_clients[session_id] = {uid: cls for uid, cls in connected_clients[session_id].items() if cls}
        if not connected_clients[session_id]:
            del connected_clients[session_id]

@app.post("/conversations")
async def add_message(message: Message, token: str = Body(...)):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (%s, %s, %s, %s, %s)",
        (message.session_id, message.role, message.content, message.timestamp,
         1 if message.role in ["assistant", "teacher"] else 0)
    )
    conn.commit()

    print(f"Saved message to database: session_id={message.session_id}, role={message.role}, content={message.content}")
    if message.role == "user":
        cursor.execute("SELECT student_id FROM chat_sessions WHERE id = %s", (message.session_id,))
        session = cursor.fetchone()
        if session:
            student_id = session[0]
            print(f"Broadcasting new message for student_id={student_id}, session_id={message.session_id}")
            await broadcast_message_to_teachers(student_id, message.session_id, message.timestamp)

    if message.role in ["teacher", "assistant"]:
        broadcast_message = {
            "session_id": message.session_id,
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp
        }
        await broadcast_message_to_clients(message.session_id, broadcast_message)

    return {"status": "ok"}

@app.post("/chatbot")
async def chatbot(request: ChatRequest = Body(...), token: str = Body(...)):
    print(f"Received /chatbot request: {request}, token: {token}")
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not request.ai_enabled:
        raise HTTPException(status_code=400, detail="AI is disabled")

    if not client:
        print("Chatbot error: Groq client not initialized")
        raise HTTPException(status_code=500, detail="AI service unavailable")

    system_prompt = {
        "role": "system",
        "content": """Bạn là **Cô Hương**, giáo viên Tin học cấp 3, chuyên dạy về an toàn thông tin. 
- Khi trả lời học sinh, luôn xưng "cô" và gọi người dùng là "em", tuyệt đối không dùng "mình", "tớ" hay "chúng ta". 
- Giọng văn ấm áp, thân thiện, dí dỏm như cô giáo đang nói chuyện trực tiếp với học sinh. 
- Giải thích ngắn gọn, dễ hiểu, ưu tiên ví dụ đời thường thay vì thuật ngữ phức tạp. 
- Khi cảnh báo về lừa đảo thì nói nghiêm túc, rõ ràng nhưng vẫn gần gũi. 
- Có thể thêm emoji 🙂😉🚀 để tạo cảm giác thân thiện. 
- Luôn kết thúc bằng một **lời khuyên rõ ràng, dễ nhớ** cho học sinh, và xuống dòng giữa các đoạn để dễ đọc.
"""
    }

    valid_roles = {"system", "user", "assistant"}
    messages = [system_prompt]
    for m in request.messages:
        role = m.role if m.role in valid_roles else "user"
        messages.append({"role": role, "content": m.content})

    async def generate():
        full_reply = ""
        try:
            print(f"Starting Groq stream for session_id: {request.session_id}")
            print(f"Messages sent to Groq: {json.dumps(messages, ensure_ascii=False)}")
            stream = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=1,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    full_reply += content
                    print(f"Streaming chunk: {content}")
                    yield f"data: {content}\n\n".encode('utf-8')
                    await asyncio.sleep(0)
            print(f"Full AI reply: {full_reply}")
            timestamp = datetime.now(timezone.utc).isoformat()
            try:
                cursor.execute(
                    "INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (%s, %s, %s, %s, %s)",
                    (request.session_id, "assistant", full_reply, timestamp, 1)
                )
                conn.commit()
                print(f"Saved AI response to database for session_id: {request.session_id}")
                broadcast_message = {
                    "session_id": request.session_id,
                    "role": "assistant",
                    "content": full_reply,
                    "timestamp": timestamp
                }
                await broadcast_message_to_clients(request.session_id, broadcast_message)
                cursor.execute("SELECT student_id FROM chat_sessions WHERE id = %s", (request.session_id,))
                session = cursor.fetchone()
                if session:
                    student_id = session[0]
                    print(f"Broadcasting AI response to teachers for student_id={student_id}, session_id={request.session_id}")
                    await broadcast_message_to_teachers(student_id, request.session_id, timestamp)
            except Exception as db_e:
                print(f"Database error: {str(db_e)}")
                raise HTTPException(status_code=500, detail=f"Database error: {str(db_e)}")
        except Exception as e:
            error_msg = f"Error in chatbot streaming: {str(e)}"
            print(error_msg)
            yield f"data: {error_msg}\n\n".encode('utf-8')
            if "400" in str(e):
                raise HTTPException(status_code=400, detail=f"Invalid request to AI: {str(e)}")
            raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.websocket("/ws/{session_id}/{token}")
async def websocket_endpoint(websocket: WebSocket, session_id: int, token: str):
    user = verify_token(token)
    if not user:
        await websocket.close(code=1008)
        print(f"WebSocket connection rejected: Invalid token for session_id {session_id}")
        return

    user_id = user["user_id"]
    user_type = user["user_type"]

    cursor.execute("SELECT student_id FROM chat_sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()
    if not session or (user_type == "student" and session[0] != user_id):
        await websocket.close(code=1008)
        print(f"WebSocket connection rejected: Unauthorized access for session_id {session_id}, user_id {user_id}")
        return

    await websocket.accept()
    print(f"WebSocket accepted for session_id: {session_id}, user_id: {user_id}")

    if session_id not in connected_clients:
        connected_clients[session_id] = {}
    if user_id not in connected_clients[session_id]:
        connected_clients[session_id][user_id] = []
    connected_clients[session_id][user_id].append(websocket)

    try:
        async def keep_alive():
            while websocket.client_state == WebSocketState.CONNECTED:
                try:
                    await websocket.send_text(json.dumps({"type": "ping"}))
                    print(f"Sent ping for session_id: {session_id}, user_id: {user_id}")
                    await asyncio.sleep(30)
                except Exception as e:
                    print(f"Ping error for session_id {session_id}, user_id {user_id}: {str(e)}")
                    break

        asyncio.create_task(keep_alive())

        while True:
            data = await websocket.receive_text()
            print(f"Received WebSocket message for session_id {session_id}, user_id {user_id}: {data}")
            message_data = json.loads(data)
            if message_data.get("session_id") != session_id:
                print(f"Session mismatch: Received session_id {message_data.get('session_id')} on WebSocket for session_id {session_id}")
                continue
            await add_message(Message(**message_data), token)
    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected for session_id {session_id}, user_id {user_id}, code: {e.code}, reason: {e.reason}")
        if session_id in connected_clients and user_id in connected_clients[session_id]:
            if websocket in connected_clients[session_id][user_id]:
                connected_clients[session_id][user_id].remove(websocket)
            if not connected_clients[session_id][user_id]:
                del connected_clients[session_id][user_id]
            if not connected_clients[session_id]:
                del connected_clients[session_id]
    except Exception as e:
        print(f"Unexpected error in WebSocket for session_id {session_id}, user_id {user_id}: {str(e)}")
    finally:
        if session_id in connected_clients and user_id in connected_clients[session_id]:
            if websocket in connected_clients[session_id][user_id]:
                connected_clients[session_id][user_id].remove(websocket)
            if not connected_clients[session_id][user_id]:
                del connected_clients[session_id][user_id]
            if not connected_clients[session_id]:
                del connected_clients[session_id]

@app.post("/mark_read/{session_id}")
async def mark_read(session_id: int, token: str):
    user = verify_token(token)
    if not user or user["user_type"] != "teacher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("UPDATE conversations SET read_by_teacher = 1 WHERE session_id = %s AND role = 'user' AND read_by_teacher = 0",
                    (session_id,))
    conn.commit()
    return {"status": "ok"}

@app.get("/unread/{student_id}")
async def get_unread(student_id: int, token: str):
    user = verify_token(token)
    if not user or user["user_type"] != "teacher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("""
    SELECT COUNT(*) FROM conversations 
    WHERE session_id IN (SELECT id FROM chat_sessions WHERE student_id = %s) 
    AND role = 'user' AND read_by_teacher = 0
    """, (student_id,))
    count = cursor.fetchone()[0]
    return {"unread": count > 0}

@app.get("/last_message/{student_id}")
async def get_last_message(student_id: int, token: str):
    user = verify_token(token)
    if not user or user["user_type"] != "teacher":
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("""
    SELECT MAX(timestamp) FROM conversations 
    WHERE session_id IN (SELECT id FROM chat_sessions WHERE student_id = %s) 
    AND role = 'user'
    """, (student_id,))
    result = cursor.fetchone()[0]
    return {"last_time": result or "N/A"}

@app.get("/student/{student_id}")
async def get_student(student_id: int, token: str):
    user = verify_token(token)
    if not user or (user["user_type"] == "student" and user["user_id"] != student_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT id, name, class, gvcn FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()
    if student:
        return {"id": student[0], "name": student[1], "class": student[2], "gvcn": student[3]}
    raise HTTPException(status_code=404, detail="Student not found")

@app.get("/student/{student_id}/latest_session")
async def get_latest_session(student_id: int, token: str):
    user = verify_token(token)
    if not user or (user["user_type"] == "student" and user["user_id"] != student_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    cursor.execute("SELECT id FROM chat_sessions WHERE student_id = %s ORDER BY created_at DESC LIMIT 1",
                    (student_id,))
    session = cursor.fetchone()
    return {"session_id": session[0] if session else None}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)