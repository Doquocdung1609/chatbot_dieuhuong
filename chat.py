import streamlit as st
from groq import Groq

# 🔑 Khởi tạo client Groq
client = Groq(api_key="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")

# Cấu hình giao diện
st.set_page_config(page_title="Chatbot Cô Hương", page_icon="👩‍🏫", layout="centered")

st.title("👩‍🏫 Chatbot Cô Hương")
st.markdown("Xin chào các em! Cô là **Hương**, giáo viên Tin học. "
            "Các em có thắc mắc gì về **phòng chống lừa đảo trên mạng** thì hãy hỏi cô nhé.")

# Lưu lịch sử hội thoại
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

# Hiển thị hội thoại cũ
for msg in st.session_state.messages[1:]:
    if msg["role"] == "user":
        st.chat_message("user").markdown(f"👦 **Học sinh**: {msg['content']}")
    else:
        st.chat_message("assistant").markdown(f"👩‍🏫 **Cô Hương**: {msg['content']}")

# Ô nhập câu hỏi
if prompt := st.chat_input("Nhập câu hỏi của em..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").markdown(f"👦 **Học sinh**: {prompt}")

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
                placeholder.markdown(f"👩‍🏫 **Cô Hương**: {full_reply}▌")  # hiệu ứng đang gõ

        # Xóa ký hiệu gõ ▌ sau khi xong
        placeholder.markdown(f"👩‍🏫 **Cô Hương**: {full_reply}")

    # Lưu câu trả lời
    st.session_state.messages.append({"role": "assistant", "content": full_reply})
