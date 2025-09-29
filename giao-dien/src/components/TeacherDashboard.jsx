import { useState, useEffect } from 'react';
import { getStudents, getUnread, getLastMessage, createSession, getSessions, getConversations } from '../services/api';
import Chat from './Chat';

const TeacherDashboard = ({ aiEnabled, setAiEnabled, token }) => {
  const [students, setStudents] = useState([]);
  const [filters, setFilters] = useState({ name: '', class: '', gvcn: '' });
  const [view, setView] = useState('home');
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [currentSession, setCurrentSession] = useState(null);

  useEffect(() => {
  if (token) {
    console.log('Fetching students with token:', token);
    getStudents(token)
      .then(res => {
        console.log('getStudents response:', res.data);
        Promise.all(
          res.data.map(async s => {
            const unread = await getUnread(s.id, token);
            const last = await getLastMessage(s.id, token);
            return {
              ...s,
              unread: unread.data.unread ? 'Chưa đọc' : 'Đã đọc',
              last_time: last.data.last_time,
            };
          })
        )
          .then(updated => {
            console.log('Updated students:', updated);
            setStudents(updated);
          })
          .catch(err => {
            console.error('Error processing students:', err);
          });
      })
      .catch(err => {
        console.error('Fetch students error:', err.response?.data, err.response?.status);
        if (err.response?.status === 401) {
          console.log('Redirecting to /login due to 401 error');
          window.location.href = '/login';
        }
      });
  }
}, [token]);

  const handleFilter = (e) => {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  };

  const filteredStudents = students.filter(s =>
    s.name.includes(filters.name) && s.class.includes(filters.class) && s.gvcn.includes(filters.gvcn)
  );

  const handleReply = async (studentId) => {
    try {
      setSelectedStudent(studentId);
      const sessionsRes = await getSessions(studentId, token);
      const sessions = sessionsRes.data;
      console.log(`Fetched sessions for student ${studentId}:`, sessions);
      
      if (sessions.length > 0) {
        let latestSessionId = null;
        let latestMessageTime = null;
        
        for (const session of sessions) {
          const conversationsRes = await getConversations(session.id, token);
          const messages = conversationsRes.data;
          if (messages.length > 0) {
            const latestMessage = messages[messages.length - 1];
            if (!latestMessageTime || latestMessage.timestamp > latestMessageTime) {
              latestMessageTime = latestMessage.timestamp;
              latestSessionId = session.id;
            }
          }
        }
        
        if (latestSessionId) {
          console.log(`Setting session for student ${studentId}: ${latestSessionId}`);
          setCurrentSession(latestSessionId);
          setView('chat');
        } else {
          console.log(`Using latest session for student ${studentId}: ${sessions[0].id}`);
          setCurrentSession(sessions[0].id);
          setView('chat');
        }
      } else {
        const newSessionRes = await createSession(
          { student_id: studentId, title: `Chat ${new Date().toISOString()}` },
          token
        );
        console.log(`Created new session for student ${studentId}: ${newSessionRes.data.id}`);
        setCurrentSession(newSessionRes.data.id);
        setView('chat');
      }
    } catch (err) {
      console.error('Failed to fetch or create session:', {
        message: err.message,
        stack: err.stack,
        response: err.response ? {
          status: err.response.status,
          data: err.response.data
        } : null
      });
      if (err.response?.status === 401) {
        window.location.href = '/login';
      } else {
        alert(`Không thể mở phiên chat: ${err.message}. Vui lòng thử lại.`);
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
    <div className="main p-6">
      <h1 className="text-2xl font-bold mb-4">Chatbot Cô Hương - Chế độ Giáo viên</h1>
      <label className="flex items-center mb-4">
        <input
          type="checkbox"
          checked={aiEnabled}
          onChange={(e) => setAiEnabled(e.target.checked)}
          className="mr-2"
        />
        Bật AI
      </label>
      <h2 className="text-xl font-semibold mb-4">Danh sách học sinh</h2>
      <div className="flex space-x-4 mb-4">
        <input
          name="name"
          className="p-2 border rounded"
          placeholder="Lọc tên"
          onChange={handleFilter}
        />
        <input
          name="class"
          className="p-2 border rounded"
          placeholder="Lọc lớp"
          onChange={handleFilter}
        />
        <input
          name="gvcn"
          className="p-2 border rounded"
          placeholder="Lọc GVCN"
          onChange={handleFilter}
        />
      </div>
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-gray-100">
            <th className="p-2 border">ID</th>
            <th className="p-2 border">Tên</th>
            <th className="p-2 border">Lớp</th>
            <th className="p-2 border">GVCN</th>
            <th className="p-2 border">Tin cuối</th>
            <th className="p-2 border">Trạng thái</th>
            <th className="p-2 border">Hành động</th>
          </tr>
        </thead>
        <tbody>
          {filteredStudents.map(s => (
            <tr key={s.id} className="hover:bg-gray-50">
              <td className="p-2 border">{s.id}</td>
              <td className="p-2 border">{s.name}</td>
              <td className="p-2 border">{s.class}</td>
              <td className="p-2 border">{s.gvcn}</td>
              <td className="p-2 border">{s.last_time}</td>
              <td className="p-2 border">{s.unread}</td>
              <td className="p-2 border">
                <button
                  className="p-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  onClick={() => handleReply(s.id)}
                >
                  Trả lời
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button
        className="mt-4 p-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        onClick={() => window.location.reload()}
      >
        Refresh
      </button>
    </div>
  );
};

export default TeacherDashboard;