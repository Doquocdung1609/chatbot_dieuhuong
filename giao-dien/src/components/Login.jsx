// Login.jsx
import { useState } from 'react';
import { loginStudent, teacherLogin } from '../services/api';
import { useNavigate } from 'react-router-dom';
import '../styles/auth.css';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState('Học sinh');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (mode === 'Học sinh') {
        const response = await loginStudent({ username, password });
        onLogin(response.data.id, 'Học sinh', response.data.token);
        navigate('/chat');
      } else {
        const response = await teacherLogin({ username, password });
        onLogin(response.data.id, 'Giáo viên', response.data.token);
        navigate('/teacher');
      }
    } catch (err) {
      alert('Đăng nhập thất bại: ' + (err.response?.data?.detail || 'Lỗi không xác định'));
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <h2 className="auth-title">Đăng nhập</h2>
        <form onSubmit={handleSubmit} className="auth-form">
          <select value={mode} onChange={(e) => setMode(e.target.value)} className="auth-input">
            <option value="Học sinh">Học sinh</option>
            <option value="Giáo viên">Giáo viên</option>
          </select>
          <input
            className="auth-input"
            placeholder={mode === 'Học sinh' ? 'Số điện thoại' : 'Username'}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            className="auth-input"
            type="password"
            placeholder="Mật khẩu"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="auth-button">Đăng nhập</button>
          {mode === 'Học sinh' && (
            <p className="auth-text">
              Chưa có tài khoản? <a href="/register" className="auth-link">Đăng ký</a>
            </p>
          )}
        </form>
      </div>
    </div>
  );
}

export default Login;
