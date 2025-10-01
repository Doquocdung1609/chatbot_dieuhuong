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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const location = useLocation();

  useEffect(() => {
    console.log('AppContent re-rendered with:', { userId, token, mode, location: location.pathname });
  }, [userId, token, mode, location]);

  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  return (
    <div className={`app-container flex main ${sidebarCollapsed ? 'collapsed' : ''}`}>
      {userId && token && (
        <Sidebar
          studentId={userId}
          token={token}
          currentSession={currentSession}
          setCurrentSession={setCurrentSession}
          handleLogout={handleLogout}
          isTeacher={mode === 'Giáo viên'}
          setCollapsedGlobal={setSidebarCollapsed}   // 👈 truyền xuống Sidebar
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
                  userId={userId}
                  token={token}
                  aiEnabled={aiEnabled}
                  currentSession={currentSession}
                  setCurrentSession={setCurrentSession}
                  handleLogout={handleLogout}
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

function TeacherChatWrapper({ userId, token, aiEnabled, currentSession, setCurrentSession, handleLogout }) {
  const { studentId } = useParams();
  const location = useLocation();
  const [sessionId, setSessionId] = useState(location.state?.sessionId || currentSession);

  useEffect(() => {
    if (location.state?.sessionId && location.state.sessionId !== sessionId) {
      setSessionId(location.state.sessionId);
      setCurrentSession(location.state.sessionId);
    }
  }, [location.state?.sessionId]);

  useEffect(() => {
    if (currentSession && currentSession !== sessionId) {
      setSessionId(currentSession);
    }
  }, [currentSession]);

  return (
    <div className="flex w-full">
      <Sidebar
        studentId={studentId}
        token={token}
        currentSession={sessionId}
        setCurrentSession={setCurrentSession}
        handleLogout={handleLogout}
        isTeacher={true}
      />

      <div className="flex-1">
        <Chat
          mode="Giáo viên"
          userId={userId}
          studentId={studentId}
          token={token}
          aiEnabled={aiEnabled}
          currentSession={sessionId}
          setCurrentSession={setCurrentSession}
        />
      </div>
    </div>
  );
}

