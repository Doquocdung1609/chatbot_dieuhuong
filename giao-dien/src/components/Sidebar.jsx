import { useState, useEffect, useRef } from 'react';
import { getSessions, createSession } from '../services/api';
import { ChevronLeft, ChevronRight, PlusCircle, LogOut, MessageSquare } from 'lucide-react';
import '../styles/chat.css';
import { useNavigate, useLocation } from 'react-router-dom'; // Thêm useNavigate

const Sidebar = ({
  studentId,
  token,
  currentSession,
  setCurrentSession,
  handleLogout,
  isTeacher = false,
  setCollapsedGlobal,   // 🔹 thêm prop để báo cho Chat biết
}) => {
  const [sessions, setSessions] = useState([]);
  const [collapsed, setCollapsed] = useState(false);
  const hasFetched = useRef(false);
  const hasCreatedInitialSession = useRef(false);
  const location = useLocation();
  const navigate = useNavigate();

  const isTeacherChatPage = location.pathname.startsWith('/teacher/chat');

useEffect(() => {
  if (token && studentId && !hasFetched.current) {
    hasFetched.current = true;
    fetchSessions();
  }
}, [studentId, token]);

const fetchSessions = async () => {
  try {
    const res = await getSessions(studentId, token);
    console.log('Fetched sessions:', res.data);
    setSessions(res.data);

    if (res.data.length > 0) {
      const latestSession = res.data[0].id; // Luôn đặt về session mới nhất khi tải danh sách
      console.log('Setting currentSession to latest:', latestSession);
      setCurrentSession(latestSession);
    } else if (!hasCreatedInitialSession.current) {
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
      console.log('Created new session:', res.data);
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

  const toggleSidebar = () => {
    setCollapsed(!collapsed);
    setCollapsedGlobal && setCollapsedGlobal(!collapsed); // 🔹 báo trạng thái ra ngoài
  };

  const onLogout = () => {
    handleLogout(); // Gọi hàm handleLogout để reset state
    navigate('/login'); // Điều hướng về trang đăng nhập
  };

  return (
    <aside className={`sidebar-container ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-title">
          <MessageSquare size={22} />
          {!collapsed && <span>Chatbot Cô Hương</span>}
        </div>
        <button className="toggle-btn" onClick={toggleSidebar}>
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

            {(!isTeacher || isTeacherChatPage) && (
            <div className="session-section">
              <h4 className="section-title">
                {isTeacher ? 'Phiên chat của học sinh' : 'Lịch sử trò chuyện'}
              </h4>

              {!isTeacher && (
                <button className="create-session-btn" onClick={createNewSession}>
                  <span>Tạo chat mới</span>
                </button>
              )}

              <div className="session-list">
                {sessions.length === 0 ? (
                  <p className="empty-text">Chưa có phiên chat nào</p>
                ) : (
                  sessions.map((s) => (
                    <div
                      key={s.id}
                      className={`session-item ${currentSession === s.id ? 'active' : ''}`}
                      onClick={() => {
                        console.log('Clicked session:', s.id); // Debug
                        setCurrentSession(s.id);
                      }}
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
