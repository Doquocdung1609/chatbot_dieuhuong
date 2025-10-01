// Register.jsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentRegister } from '../services/api';
import '../styles/auth.css';

function Register() {
  const [name, setName] = useState('');
  const [className, setClassName] = useState('');
  const [gvcn, setGvcn] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await studentRegister({ username, name, className, gvcn, password });
      alert('Đăng ký thành công! Vui lòng đăng nhập.');
      navigate('/login');
    } catch (err) {
      alert('Đăng ký thất bại: ' + (err.response?.data?.detail || 'Lỗi không xác định'));
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="auth-header">
          <h1 className="auth-brand">Chatbot Cô Hương</h1>
        </div>

        <h2 className="auth-title">Đăng ký</h2>

        <form onSubmit={handleSubmit} className="auth-form">
          <input className="auth-input" placeholder="Tên" value={name} onChange={(e) => setName(e.target.value)} required />
          <input className="auth-input" placeholder="Lớp" value={className} onChange={(e) => setClassName(e.target.value)} required />
          <input className="auth-input" placeholder="GVCN" value={gvcn} onChange={(e) => setGvcn(e.target.value)} required />
          <input className="auth-input" placeholder="Số điện thoại" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <input className="auth-input" type="password" placeholder="Mật khẩu" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit" className="auth-button">Đăng ký</button>
          <p className="auth-text">
            Đã có tài khoản? <a href="/login" className="auth-link">Đăng nhập</a>
          </p>
        </form>
      </div>
    </div>
  );
}

export default Register;
