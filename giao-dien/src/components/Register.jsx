import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentRegister } from '../services/api';

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
      console.error('Register error:', err);
      alert('Đăng ký thất bại: ' + (err.response?.data?.detail || 'Lỗi không xác định'));
    }
  };

  return (
    <div className="login-container">
      <h2>Đăng ký</h2>
      <form onSubmit={handleSubmit}>
        <input
          placeholder="Tên"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          placeholder="Lớp"
          value={className}
          onChange={(e) => setClassName(e.target.value)}
          required
        />
        <input
          placeholder="GVCN"
          value={gvcn}
          onChange={(e) => setGvcn(e.target.value)}
          required
        />
        <input
          placeholder="Số điện thoại"
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
        <button type="submit">Đăng ký</button>
        <p>
          Đã có tài khoản? <a href="/login">Đăng nhập</a>
        </p>
      </form>
    </div>
  );
}

export default Register;