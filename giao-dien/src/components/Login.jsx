import { useState } from 'react';
import { loginStudent, teacherLogin } from '../services/api';
import { useNavigate } from 'react-router-dom';

function Login({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mode, setMode] = useState('Học sinh');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
  e.preventDefault();
  console.log('Submitting login for mode:', mode, 'username:', username);
  if (!onLogin || typeof onLogin !== 'function') {
    console.error('onLogin prop is missing or not a function');
    alert('Lỗi hệ thống: onLogin không được cung cấp');
    return;
  }
  try {
    if (mode === 'Học sinh') {
      const response = await loginStudent({ username, password });
      console.log('Student login response:', response.data);
      onLogin(response.data.id, 'Học sinh', response.data.token);
      navigate('/chat');
      console.log('Navigated to /chat');
    } else {
      const response = await teacherLogin({ username, password });
      console.log('Teacher login response:', response.data);
      onLogin(response.data.id, 'Giáo viên', response.data.token);
      navigate('/teacher');
      console.log('Navigated to /teacher');
    }
  } catch (err) {
    console.error('Login error:', err);
    alert('Đăng nhập thất bại: ' + (err.response?.data?.detail || 'Lỗi không xác định'));
  }
};

  return (
    <div className="login-container">
      <h2>Đăng nhập</h2>
      <form onSubmit={handleSubmit}>
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="Học sinh">Học sinh</option>
          <option value="Giáo viên">Giáo viên</option>
        </select>
        <input
          placeholder={mode === 'Học sinh' ? 'Số điện thoại' : 'Username'}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Mật khẩu"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit">Đăng nhập</button>
        {mode === 'Học sinh' && (
          <p>
            Chưa có tài khoản? <a href="/register">Đăng ký</a>
          </p>
        )}
      </form>
    </div>
  );
}

export default Login;