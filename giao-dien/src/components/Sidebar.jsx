import { useState, useEffect, useRef } from 'react';
import { getSessions, createSession } from '../services/api';
import { ChevronLeft, ChevronRight, PlusCircle, LogOut, MessageSquare } from 'lucide-react';
import '../styles/chat.css';

const Sidebar = ({
  studentId,
  token,
  currentSession,
  setCurrentSession,
  handleLogout,
  isTeacher = false
}) => {
  const [sessions, setSessions] = useState([]);
  const [collapsed, setCollapsed] = useState(false);
  const hasFetched = useRef(false);
  const hasCreatedInitialSession = useRef(false);

  useEffect(() => {
  if (token && !hasFetched.current) {
    hasFetched.current = true;
    if (isTeacher) {
      console.log('Teacher logged in → skip fetching student sessions');
      return; // hoặc gọi fetchTeacherSessions() nếu có
    }
    if (studentId) fetchSessions();
  }
}, [studentId, token, isTeacher]);

  const fetchSessions = async () => {
    try {
      const res = await getSessions(studentId, token);
      setSessions(res.data);

      if (res.data.length > 0 && !currentSession) {
        setCurrentSession(res.data[0].id);
      } else if (res.data.length === 0 && !hasCreatedInitialSession.current) {
        hasCreatedInitialSession.current = true;
        createNewSession();
      }
    } catch (err) {
      console.error('Fetch sessions error:', err);
      if (err.response?.status === 401) window.location.href = '/login';
    }
  };

  const createNewSession = async () => {
    try {
      const title = `Chat ${new Date().toLocaleString()}`;
      const res = await createSession({ student_id: studentId, title }, token);
      setSessions((prev) => [
        { id: res.data.id, title, created_at: new Date().toISOString() },
        ...prev,
      ]);
      setCurrentSession(res.data.id);
    } catch (err) {
      console.error('Create session error:', err);
      if (err.response?.status === 401) window.location.href = '/login';
    }
  };

 return (
  <aside className={`sidebar-container ${collapsed ? 'collapsed' : ''}`}>
    <div className="sidebar-header">
      <div className="sidebar-title">
        <MessageSquare size={22} />
        {!collapsed && <span>Chatbot Cô Hương</span>}
      </div>
      <button className="toggle-btn" onClick={() => setCollapsed(!collapsed)}>
        {collapsed ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
      </button>
    </div>

    {!collapsed && (
      <>
        {studentId && (
          <button className="logout-btn" onClick={handleLogout}>
            <LogOut size={18} />
            <span>Đăng xuất</span>
          </button>
        )}

        {!isTeacher && (
          <div className="session-section">
            <h4 className="section-title">Lịch sử trò chuyện</h4>

            <button className="create-session-btn" onClick={createNewSession}>
              <PlusCircle size={18} />
              <span>Tạo chat mới</span>
            </button>

            <div className="session-list">
              {sessions.length === 0 ? (
                <p className="empty-text">Chưa có phiên chat nào</p>
              ) : (
                sessions.map((s) => (
                  <div
                    key={s.id}
                    className={`session-item ${currentSession === s.id ? 'active' : ''}`}
                    onClick={() => setCurrentSession(s.id)}
                  >
                    <span>{s.title}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </>
    )}
  </aside>
);
};

export default Sidebar;
