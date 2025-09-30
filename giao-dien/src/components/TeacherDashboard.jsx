import { useState, useEffect } from 'react';
import {
  getStudents,
  getUnread,
  getLastMessage,
  createSession,
  getSessions,
  getConversations,
  markRead   
} from '../services/api';
import Chat from './Chat';
import '../styles/teacher-dashboard.css';
import { FiRefreshCcw, FiFilter, FiMessageCircle } from 'react-icons/fi';
import { useNavigate } from "react-router-dom";

const formatDate = (isoString) => {
  if (!isoString) return '—';
  const date = new Date(isoString);
  return date.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).replace(',', '');
};



const TeacherDashboard = ({ aiEnabled, setAiEnabled, token }) => {
  const [students, setStudents] = useState([]);
  const [filters, setFilters] = useState({ name: '', class: '', gvcn: '' });
  const [view, setView] = useState('home');
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);
  const navigate = useNavigate();

  const fetchStudents = async () => {
    if (!token) return;
    try {
      const res = await getStudents(token);
      const updated = await Promise.all(
        res.data.map(async (s) => {
          const unread = await getUnread(s.id, token);
          const last = await getLastMessage(s.id, token);
          return {
            ...s,
            unread: unread.data.unread ? 'Chưa đọc' : 'Đã đọc',
            last_time: last.data.last_time,
          };
        })
      );
      setStudents(updated);
    } catch (err) {
      if (err.response?.status === 401) window.location.href = '/login';
    }
  };


  useEffect(() => {
    fetchStudents();
  }, [token]);

  const handleFilter = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const filteredStudents = students.filter(
    (s) =>
      s.name.toLowerCase().includes(filters.name.toLowerCase()) &&
      s.class.toLowerCase().includes(filters.class.toLowerCase()) &&
      s.gvcn.toLowerCase().includes(filters.gvcn.toLowerCase())
  );

const handleReply = async (studentId) => {
  try {
    setSelectedStudent(studentId);
    const sessionsRes = await getSessions(studentId, token);
    const sessions = sessionsRes.data;

    let sessionIdToUse = null;
    if (sessions.length > 0) {
      sessionIdToUse = sessions[0].id;
      let latestMessageTime = null;

      for (const session of sessions) {
        const conversationsRes = await getConversations(session.id, token);
        const messages = conversationsRes.data;
        if (messages.length > 0) {
          const latestMessage = messages[messages.length - 1];
          if (!latestMessageTime || latestMessage.timestamp > latestMessageTime) {
            latestMessageTime = latestMessage.timestamp;
            sessionIdToUse = session.id;
          }
        }
      }
    } else {
      const newSessionRes = await createSession(
        { student_id: studentId, title: `Chat ${new Date().toISOString()}` },
        token
      );
      sessionIdToUse = newSessionRes.data.id;
    }

    // ✅ Đánh dấu là đã đọc khi giáo viên mở chat
    await markRead(sessionIdToUse, token);

    setCurrentSession(sessionIdToUse);
    setView('chat');
    navigate(`/teacher/chat/${studentId}`, { state: { sessionId: sessionIdToUse } });
  } catch (err) {
    if (err.response?.status === 401) {
      window.location.href = '/login';
    } else {
      alert(`Không thể mở phiên chat: ${err.message}`);
    }
  }
};


  if (view === 'chat') {
    return (
      <Chat
        mode="Giáo viên"
        userId={selectedStudent}
        token={token}
        currentSession={currentSession}
        setCurrentSession={setCurrentSession}
        aiEnabled={aiEnabled}
      />
    );
  }

  return (
    <div className="teacher-dashboard">
      <div className="dashboard-header">
        <h1>📚 Chatbot Cô Hương - Chế độ Giáo viên</h1>
        <div className="header-actions">
          <label className="ai-toggle">
            <input
              type="checkbox"
              checked={aiEnabled}
              onChange={(e) => setAiEnabled(e.target.checked)}
            />
            <span>Bật AI</span>
          </label>
          <button className="refresh-btn" onClick={fetchStudents}>
            <FiRefreshCcw size={18} /> Làm mới
          </button>
        </div>
      </div>

      <div className="filter-section">
        <FiFilter className="filter-icon" />
        <input
          name="name"
          placeholder="Lọc theo tên"
          value={filters.name}
          onChange={handleFilter}
        />
        <input
          name="class"
          placeholder="Lọc theo lớp"
          value={filters.class}
          onChange={handleFilter}
        />
        <input
          name="gvcn"
          placeholder="Lọc theo GVCN"
          value={filters.gvcn}
          onChange={handleFilter}
        />
      </div>

      <div className="table-container">
        <table className="student-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên</th>
              <th>Lớp</th>
              <th>GVCN</th>
              <th>Tin cuối</th>
              <th>Trạng thái</th>
              <th>Hành động</th>
            </tr>
          </thead>
          <tbody>
            {filteredStudents.map((s) => (
              <tr key={s.id}>
                <td>{s.id}</td>
                <td>{s.name}</td>
                <td>{s.class}</td>
                <td>{s.gvcn}</td>
                <td>{formatDate(s.last_time)}</td>
                <td>
                  <span className={`status ${s.unread === 'Chưa đọc' ? 'unread' : 'read'}`}>
                    {s.unread}
                  </span>
                </td>
                <td>
                  <button className="reply-btn" onClick={() => handleReply(s.id)}>
                    <FiMessageCircle size={16} /> Trả lời
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TeacherDashboard;
