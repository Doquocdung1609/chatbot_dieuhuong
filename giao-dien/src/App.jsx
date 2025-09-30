import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useLocation, useParams } from 'react-router-dom';
import Login from './components/Login';
import Register from './components/Register';
import Chat from './components/Chat';
import TeacherDashboard from './components/TeacherDashboard';
import Sidebar from './components/Sidebar';
import './index.css';

function App() {
  const [mode, setMode] = useState('Học sinh');
  const [userId, setUserId] = useState(null);
  const [token, setToken] = useState(null);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [currentSession, setCurrentSession] = useState(null);

  const handleLogin = (id, selectedMode, authToken) => {
    console.log('handleLogin called with:', { id, selectedMode, authToken });
    setUserId(id);
    setMode(selectedMode);
    setToken(authToken);
  };

  const handleLogout = () => {
    setUserId(null);
    setToken(null);
    setCurrentSession(null);
  };

  return (
    <Router>
      <AppContent
        mode={mode}
        userId={userId}
        token={token}
        aiEnabled={aiEnabled}
        currentSession={currentSession}
        setCurrentSession={setCurrentSession}
        setAiEnabled={setAiEnabled}
        handleLogin={handleLogin}
        handleLogout={handleLogout}
      />
    </Router>
  );
}

function AppContent({
  mode,
  userId,
  token,
  aiEnabled,
  currentSession,
  setCurrentSession,
  setAiEnabled,
  handleLogin,
  handleLogout,
}) {
  const location = useLocation();

  useEffect(() => {
    console.log('AppContent re-rendered with:', { userId, token, mode, location: location.pathname });
  }, [userId, token, mode, location]);

  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  return (
    <div className="app-container flex">
      {/* ✅ Chỉ hiển thị Sidebar sau khi đăng nhập */}
      {userId && token && (
        <Sidebar
          studentId={userId}
          token={token}
          currentSession={currentSession}
          setCurrentSession={setCurrentSession}
          handleLogout={handleLogout}
          isTeacher={mode === 'Giáo viên'}
        />
      )}

      <main className={`main-content ${userId && token ? 'ml-64' : ''} p-6 w-full`}>
        <Routes>
          <Route path="/login" element={<Login onLogin={handleLogin} mode={mode} />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/chat"
            element={
              userId && token ? (
                <Chat
                  mode={mode}
                  userId={userId}
                  token={token}
                  aiEnabled={aiEnabled}
                  currentSession={currentSession}
                  setCurrentSession={setCurrentSession}
                />
              ) : (
                <Navigate to="/login" />
              )
            }
          />

          <Route
            path="/teacher"
            element={
              userId && token && mode === 'Giáo viên' ? (
                <TeacherDashboard
                  userId={userId}
                  token={token}
                  aiEnabled={aiEnabled}
                  setAiEnabled={setAiEnabled}
                  currentSession={currentSession}
                  setCurrentSession={setCurrentSession}
                  handleLogout={handleLogout}
                />
              ) : (
                <Navigate to="/login" />
              )
            }
          />

          <Route
  path="/teacher/chat/:studentId"
  element={
    userId && token && mode === "Giáo viên" ? (
      <TeacherChatWrapper
        token={token}
        aiEnabled={aiEnabled}
        currentSession={currentSession}
        setCurrentSession={setCurrentSession}
      />
    ) : (
      <Navigate to="/login" />
    )
  }
/>

          {/* Mặc định điều hướng về login */}
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;

function TeacherChatWrapper({ token, aiEnabled, currentSession, setCurrentSession }) {
  const { studentId } = useParams();
  const location = useLocation();
  const sessionId = location.state?.sessionId || currentSession;

  return (
    <Chat
      mode="Giáo viên"
      userId={parseInt(studentId)}   // ✅ studentId chứ không phải teacherId
      token={token}
      aiEnabled={aiEnabled}
      currentSession={sessionId}
      setCurrentSession={setCurrentSession}
    />
  );
}
