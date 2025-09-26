import streamlit as st
from groq import Groq
import sqlite3
from datetime import datetime
import pandas as pd
import time

# 🔑 Khởi tạo client Groq
import os
from dotenv import load_dotenv
load_dotenv()
client = Groq(api_key=os.environ["OPENAI_API_KEY"])

# Kết nối SQLite database
conn = sqlite3.connect('student_management.db', check_same_thread=False)
cursor = conn.cursor()

# Tạo bảng nếu chưa tồn tại
cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    name TEXT,
    class TEXT,
    gvcn TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    title TEXT,
    created_at TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    role TEXT,
    content TEXT,
    timestamp TEXT,
    read_by_teacher INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
)
''')
conn.commit()

# Migration for old database schema
cursor.execute("PRAGMA table_info(conversations)")
column_info = cursor.fetchall()
columns = [info[1] for info in column_info]

if 'session_id' not in columns:
    cursor.execute("ALTER TABLE conversations ADD COLUMN session_id INTEGER")
    conn.commit()

    if 'student_id' in columns:
        cursor.execute("SELECT DISTINCT student_id FROM conversations")
        unique_students = cursor.fetchall()
        if unique_students:
            session_map = {}
            for (sid,) in unique_students:
                timestamp = datetime.now()
                title = f"Legacy Chat {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                cursor.execute("INSERT INTO chat_sessions (student_id, title, created_at) VALUES (?, ?, ?)", (sid, title, timestamp.isoformat()))
                conn.commit()
                session_map[sid] = cursor.lastrowid
            for sid, session_id in session_map.items():
                cursor.execute("UPDATE conversations SET session_id = ? WHERE student_id = ?", (session_id, sid))
                conn.commit()

if 'read_by_teacher' not in columns:
    cursor.execute("ALTER TABLE conversations ADD COLUMN read_by_teacher INTEGER DEFAULT 0")
    conn.commit()

# Cấu hình giao diện
st.set_page_config(page_title="Chatbot Cô Hương", page_icon="👩‍🏫", layout="wide")

# Sidebar chọn chế độ
mode = st.sidebar.selectbox("Chọn chế độ", ["Học sinh", "Giáo viên"])

# Lưu trạng thái AI (mặc định bật)
if "ai_enabled" not in st.session_state:
    st.session_state["ai_enabled"] = True

# Hàm để hiển thị chat messages từ DB
def display_chat_messages(session_id, title):
    st.title(title)
    cursor.execute("SELECT role, content, timestamp FROM conversations WHERE session_id = ? ORDER BY timestamp",
                   (session_id,))
    messages = cursor.fetchall()
    for msg in messages:
        role, content, _ = msg
        if role == "user":
            st.chat_message("user").write(f"👦 **Học sinh**: {content}")
        elif role == "assistant":
            st.chat_message("assistant").write(f"👩‍🏫 **Cô Hương (AI)**: {content}")
        elif role == "teacher":
            st.chat_message("assistant").write(f"👩‍🏫 **Cô Hương**: {content}")

# Hàm lấy thời gian tin nhắn cuối cùng
def get_last_message_time(student_id):
    cursor.execute("""
    SELECT MAX(timestamp) FROM conversations 
    WHERE session_id IN (SELECT id FROM chat_sessions WHERE student_id = ?) 
    AND role = 'user'
    """, (student_id,))
    result = cursor.fetchone()[0]
    return result if result else "N/A"

# Hàm lấy trạng thái chưa đọc
def get_unread_status(student_id):
    cursor.execute("""
    SELECT COUNT(*) FROM conversations 
    WHERE session_id IN (SELECT id FROM chat_sessions WHERE student_id = ?) 
    AND role = 'user' AND read_by_teacher = 0
    """, (student_id,))
    count = cursor.fetchone()[0]
    return "Chưa đọc" if count > 0 else "Đã đọc"

# Hàm lấy session mới nhất
def get_latest_session(student_id):
    cursor.execute("""
    SELECT id FROM chat_sessions WHERE student_id = ? 
    ORDER BY created_at DESC LIMIT 1
    """, (student_id,))
    result = cursor.fetchone()
    return result[0] if result else None

# Chế độ Học sinh
if mode == "Học sinh":
    st.title("👩‍🏫 Chatbot Cô Hương - Chế độ Học sinh")
    st.write("Xin chào các em! Cô là **Hương**, giáo viên Tin học. "
             "Các em có thắc mắc gì về **phòng chống lừa đảo trên mạng** thì hãy hỏi cô nhé.")

    # Login cho học sinh
    if "student_id" not in st.session_state:
        st.subheader("Đăng nhập")
        name = st.text_input("Tên học sinh")
        class_name = st.text_input("Lớp")
        gvcn = st.text_input("GVCN")
        username = st.text_input("Số điện thoại")

        if st.button("Đăng nhập"):
            if name and class_name and gvcn and username:
                # Kiểm tra nếu username tồn tại, nếu không tạo mới
                cursor.execute("SELECT id FROM students WHERE username = ?", (username,))
                result = cursor.fetchone()
                if result:
                    st.session_state["student_id"] = result[0]
                else:
                    cursor.execute("INSERT INTO students (username, name, class, gvcn) VALUES (?, ?, ?, ?)",
                                   (username, name, class_name, gvcn))
                    conn.commit()
                    st.session_state["student_id"] = cursor.lastrowid
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Vui lòng nhập đầy đủ thông tin.")
    else:
        # Lấy thông tin học sinh
        cursor.execute("SELECT name, class, gvcn FROM students WHERE id = ?", (st.session_state["student_id"],))
        student_info = cursor.fetchone()
        if student_info is None:
            st.error("Thông tin học sinh không tìm thấy. Vui lòng đăng nhập lại.")
            del st.session_state["student_id"]
            st.rerun()
        else:
            st.write(f"Chào em {student_info[0]} lớp {student_info[1]}!")

        if st.button("Sign out"):
            del st.session_state["student_id"]
            if "current_session_id" in st.session_state:
                del st.session_state["current_session_id"]
            if "messages" in st.session_state:
                del st.session_state["messages"]
            st.rerun()

        # Sidebar cho lịch sử chat sessions
        st.sidebar.title("Lịch sử cuộc trò chuyện")
        cursor.execute("SELECT id, title FROM chat_sessions WHERE student_id = ? ORDER BY created_at DESC",
                       (st.session_state["student_id"],))
        sessions = cursor.fetchall()

        session_options = {title: id for id, title in sessions}
        if st.sidebar.button("Tạo chat mới"):
            timestamp = datetime.now()
            title = f"Chat {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            cursor.execute("INSERT INTO chat_sessions (student_id, title, created_at) VALUES (?, ?, ?)",
                           (st.session_state["student_id"], title, timestamp.isoformat()))
            conn.commit()
            st.session_state["current_session_id"] = cursor.lastrowid
            st.session_state["messages"] = [{"role": "system", "content": st.session_state["messages"][0]["content"]}] if "messages" in st.session_state else []
            st.rerun()

        selected_title = st.sidebar.selectbox("Chọn cuộc trò chuyện", list(session_options.keys()))
        if selected_title:
            st.session_state["current_session_id"] = session_options[selected_title]

        # Nếu chưa có session hiện tại, tạo mới
        if "current_session_id" not in st.session_state:
            timestamp = datetime.now()
            title = f"Chat {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            cursor.execute("INSERT INTO chat_sessions (student_id, title, created_at) VALUES (?, ?, ?)",
                           (st.session_state["student_id"], title, timestamp.isoformat()))
            conn.commit()
            st.session_state["current_session_id"] = cursor.lastrowid

        # Nút refresh để tải lại messages từ DB
        if st.button("Refresh chat"):
            st.rerun()

        # Hiển thị chat
        cursor.execute("SELECT title FROM chat_sessions WHERE id = ?", (st.session_state["current_session_id"],))
        result = cursor.fetchone()
        if result is None:
            st.error("Phiên chat không tìm thấy.")
            del st.session_state["current_session_id"]
            st.rerun()
        else:
            chat_title = result[0]
            display_chat_messages(st.session_state["current_session_id"], chat_title)

        # Lưu system prompt nếu chưa có
        if "messages" not in st.session_state:
            st.session_state["messages"] = [
                {
                    "role": "system",
                    "content": """Bạn là **Cô Hương**, giáo viên Tin học cấp 3, chuyên dạy về an toàn thông tin. 
- Khi trả lời học sinh, luôn xưng "cô" và gọi người dùng là "em", tuyệt đối không dùng "mình", "tớ" hay "chúng ta". 
- Giọng văn ấm áp, thân thiện, dí dỏm như cô giáo đang nói chuyện trực tiếp với học sinh. 
- Giải thích ngắn gọn, dễ hiểu, ưu tiên ví dụ đời thường thay vì thuật ngữ phức tạp. 
- Khi cảnh báo về lừa đảo thì nói nghiêm túc, rõ ràng nhưng vẫn gần gũi. 
- Có thể thêm emoji 🙂😉🚀 để tạo cảm giác thân thiện. 
- Luôn kết thúc bằng một **lời khuyên rõ ràng, dễ nhớ** cho học sinh. 
"""
                }
            ]

        # Ô nhập câu hỏi
        if prompt := st.chat_input("Nhập câu hỏi của em..."):
            # Lưu vào DB
            timestamp = datetime.now()
            cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (?, ?, ?, ?, ?)",
                           (st.session_state["current_session_id"], "user", prompt, timestamp.isoformat(), 0))
            conn.commit()

            st.chat_message("user").write(f"👦 **Học sinh**: {prompt}")

            # Kiểm tra nếu AI bật
            if st.session_state["ai_enabled"]:
                st.session_state.messages.append({"role": "user", "content": prompt})

                # Tạo container để stream nội dung
                with st.chat_message("assistant"):
                    placeholder = st.empty()
                    full_reply = ""

                    # 🟢 Streaming từ Groq
                    stream = client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=st.session_state.messages,
                        temperature=0.7,
                        max_completion_tokens=1024,
                        top_p=1,
                        reasoning_effort="medium",
                        stream=True  # bật chế độ stream
                    )

                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            full_reply += chunk.choices[0].delta.content
                            placeholder.write(f"👩‍🏫 **Cô Hương**: {full_reply}▌")  # hiệu ứng đang gõ

                    # Xóa ký hiệu gõ ▌ sau khi xong
                    placeholder.write(f"👩‍🏫 **Cô Hương**: {full_reply}")

                # Lưu câu trả lời AI vào DB
                cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (?, ?, ?, ?, ?)",
                               (st.session_state["current_session_id"], "assistant", full_reply, datetime.now().isoformat(), 1))
                conn.commit()

                st.session_state.messages.append({"role": "assistant", "content": full_reply})
            else:
                st.info("AI đang tắt. Cô giáo sẽ trả lời trực tiếp sau.")

# Chế độ Giáo viên
elif mode == "Giáo viên":
    st.title("👩‍🏫 Chatbot Cô Hương - Chế độ Giáo viên")

    # Login cho giáo viên
    if "teacher_logged_in" not in st.session_state:
        st.subheader("Đăng nhập giáo viên")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Đăng nhập"):
            if username == "teacher" and password == "123456":
                st.session_state["teacher_logged_in"] = True
                st.session_state["teacher_view"] = "home"
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Sai thông tin đăng nhập.")
    else:
        st.write("Chào cô Hương! Đây là trang quản trị.")

        if st.button("Sign out"):
            del st.session_state["teacher_logged_in"]
            if "teacher_view" in st.session_state:
                del st.session_state["teacher_view"]
            if "selected_student_id" in st.session_state:
                del st.session_state["selected_student_id"]
            if "current_session_id" in st.session_state:
                del st.session_state["current_session_id"]
            st.rerun()

        # Công tắc Bật/Tắt AI
        st.session_state["ai_enabled"] = st.checkbox("Bật AI (nếu tắt, học sinh chỉ nhận trả lời từ cô)", value=st.session_state["ai_enabled"])

        if "teacher_view" not in st.session_state:
            st.session_state["teacher_view"] = "home"

        if st.session_state["teacher_view"] == "home":
            # Xem danh sách học sinh
            st.subheader("Danh sách học sinh")

            # Lọc theo tên, lớp, GVCN
            filter_name = st.text_input("Lọc theo tên")
            filter_class = st.text_input("Lọc theo lớp")
            filter_gvcn = st.text_input("Lọc theo GVCN")

            query = "SELECT id, name, class, gvcn FROM students WHERE 1=1"
            params = []
            if filter_name:
                query += " AND name LIKE ?"
                params.append(f"%{filter_name}%")
            if filter_class:
                query += " AND class LIKE ?"
                params.append(f"%{filter_class}%")
            if filter_gvcn:
                query += " AND gvcn LIKE ?"
                params.append(f"%{filter_gvcn}%")

            cursor.execute(query, params)
            filtered_students = cursor.fetchall()
            if filtered_students:
                # Hiển thị header
                col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 2, 1, 2, 2, 1, 1])
                col1.write("ID")
                col2.write("Tên")
                col3.write("Lớp")
                col4.write("GVCN")
                col5.write("Tin nhắn cuối")
                col6.write("Trạng thái")
                col7.write("Hành động")

                for student in filtered_students:
                    student_id, name, class_name, gvcn = student
                    last_time = get_last_message_time(student_id)
                    status = get_unread_status(student_id)
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 2, 1, 2, 2, 1, 1])
                    col1.write(student_id)
                    col2.write(name)
                    col3.write(class_name)
                    col4.write(gvcn)
                    col5.write(last_time)
                    col6.write(status)
                    if col7.button("Trả lời", key=f"reply_{student_id}"):
                        st.session_state["selected_student_id"] = student_id
                        latest_session = get_latest_session(student_id)
                        if latest_session:
                            st.session_state["current_session_id"] = latest_session
                            st.session_state["teacher_view"] = "chat"
                        else:
                            timestamp = datetime.now()
                            title = f"Chat {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                            cursor.execute("INSERT INTO chat_sessions (student_id, title, created_at) VALUES (?, ?, ?)",
                                           (student_id, title, timestamp.isoformat()))
                            conn.commit()
                            st.session_state["current_session_id"] = cursor.lastrowid
                            st.session_state["teacher_view"] = "chat"
                        st.rerun()
            else:
                st.info("Chưa có học sinh nào.")

            if st.button("Refresh list"):
                st.rerun()

        elif st.session_state["teacher_view"] == "chat_list":
            student_id = st.session_state.get("selected_student_id")
            if student_id is None:
                st.error("Không có học sinh được chọn.")
                st.session_state["teacher_view"] = "home"
                st.rerun()
            cursor.execute("SELECT name FROM students WHERE id = ?", (student_id,))
            result = cursor.fetchone()
            if result is None:
                st.error("Học sinh không tìm thấy.")
                st.session_state["teacher_view"] = "home"
                st.rerun()
            else:
                student_name = result[0]
                st.subheader(f"Danh sách chat của học sinh {student_name}")

            cursor.execute("SELECT id, title FROM chat_sessions WHERE student_id = ? ORDER BY created_at DESC",
                           (student_id,))
            sessions = cursor.fetchall()
            session_options = {title: id for id, title in sessions}

            selected_title = st.selectbox("Chọn tab chat", list(session_options.keys()))
            if selected_title:
                st.session_state["current_session_id"] = session_options[selected_title]
                st.session_state["teacher_view"] = "chat"
                st.rerun()

            if st.button("Quay lại trang chủ"):
                st.session_state["teacher_view"] = "home"
                st.rerun()

        elif st.session_state["teacher_view"] == "chat":
            session_id = st.session_state.get("current_session_id")
            if session_id is None:
                st.error("Không có phiên chat được chọn.")
                st.session_state["teacher_view"] = "chat_list"
                st.rerun()
            cursor.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
            result = cursor.fetchone()
            if result is None:
                st.error("Phiên chat không tìm thấy.")
                st.session_state["teacher_view"] = "chat_list"
                st.rerun()
            else:
                chat_title = result[0]

            # Cập nhật trạng thái đã đọc
            cursor.execute("UPDATE conversations SET read_by_teacher = 1 WHERE session_id = ? AND role = 'user' AND read_by_teacher = 0", (session_id,))
            conn.commit()

            # Nút refresh
            if st.button("Refresh chat"):
                st.rerun()

            display_chat_messages(session_id, chat_title)

            # Trả lời trực tiếp
            direct_reply = st.chat_input("Nhập câu trả lời của cô...")
            if direct_reply:
                timestamp = datetime.now()
                cursor.execute("INSERT INTO conversations (session_id, role, content, timestamp, read_by_teacher) VALUES (?, ?, ?, ?, ?)",
                               (session_id, "teacher", direct_reply, timestamp.isoformat(), 1))
                conn.commit()
                st.chat_message("assistant").write(f"👩‍🏫 **Cô Hương**: {direct_reply}")
                st.rerun()

            if st.button("Quay lại danh sách chat"):
                st.session_state["teacher_view"] = "chat_list"
                st.rerun()