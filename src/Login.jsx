import React, { useState } from 'react';
import db from './db.json';
import './Login.css';

const Login = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const user = db.users.find((u) => u.email === email);
    if (user) {
      onLogin(user);
    } else {
      setError('Invalid email. Please try again.');
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>Welcome to FINSIGHT</h2>
        <p>Please log in with your email</p>
        <form onSubmit={handleSubmit} className="login-form">
          <input
            type="email"
            placeholder="Email Address"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="login-input"
          />
          {error && <p className="login-error">{error}</p>}
          <button type="submit" className="login-btn">
            Log In
          </button>
        </form>
      </div>
    </div>
  );
};

export default Login;
