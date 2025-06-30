import React, { useState } from 'react';
import styled from 'styled-components';

const AuthContainer = styled.div`
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 1rem;
  padding: 2rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid rgba(255, 255, 255, 0.2);
`;

const AuthTitle = styled.h2`
  color: white;
  text-align: center;
  margin-bottom: 1.5rem;
  font-weight: 300;
`;

const AuthForm = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

const Input = styled.input`
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 0.5rem;
  padding: 0.75rem;
  color: white;
  font-size: 1rem;
  
  &::placeholder {
    color: rgba(255, 255, 255, 0.7);
  }
  
  &:focus {
    outline: none;
    border-color: #ffd700;
    background: rgba(255, 255, 255, 0.15);
  }
`;

const Button = styled.button`
  background: linear-gradient(135deg, #ffd700, #ffed4e);
  color: #333;
  border: none;
  padding: 0.75rem;
  border-radius: 0.5rem;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s ease;
  margin-top: 0.5rem;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

const SecondaryButton = styled.button`
  background: transparent;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 0.5rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
  
  &:hover {
    background: rgba(255, 255, 255, 0.1);
  }
`;

const ErrorMessage = styled.div`
  color: #ff6b6b;
  background: rgba(255, 107, 107, 0.1);
  border: 1px solid rgba(255, 107, 107, 0.3);
  padding: 0.75rem;
  border-radius: 0.5rem;
  text-align: center;
`;

const SuccessMessage = styled.div`
  color: #51cf66;
  background: rgba(81, 207, 102, 0.1);
  border: 1px solid rgba(81, 207, 102, 0.3);
  padding: 0.75rem;
  border-radius: 0.5rem;
  text-align: center;
`;

const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://pdf-converter-api-gateway.onrender.com';

const AuthFormComponent = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    fullName: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin 
        ? { email: formData.email, password: formData.password }
        : { email: formData.email, password: formData.password, full_name: formData.fullName };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (result.success) {
        if (isLogin) {
          // Login successful
          setSuccess('Login successful!');
          const userData = {
            token: result.data.access_token,
            user_id: result.data.user_id,
            email: formData.email
          };
          localStorage.setItem('authToken', result.data.access_token);
          localStorage.setItem('userData', JSON.stringify(userData));
          setTimeout(() => onAuthSuccess(userData), 1000);
        } else {
          // Registration successful
          setSuccess('Registration successful! Please login.');
          setIsLogin(true);
          setFormData({ email: formData.email, password: '', fullName: '' });
        }
      } else {
        setError(result.message || 'Authentication failed');
      }
    } catch (error) {
      setError('Network error. Please try again.');
      console.error('Auth error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContainer>
      <AuthTitle>
        <i className="fas fa-user-circle" style={{ marginRight: '0.5rem' }}></i>
        {isLogin ? 'Login' : 'Create Account'}
      </AuthTitle>
      
      {error && <ErrorMessage>{error}</ErrorMessage>}
      {success && <SuccessMessage>{success}</SuccessMessage>}
      
      <AuthForm onSubmit={handleSubmit}>
        {!isLogin && (
          <Input
            type="text"
            name="fullName"
            placeholder="Full Name"
            value={formData.fullName}
            onChange={handleInputChange}
            required
          />
        )}
        
        <Input
          type="email"
          name="email"
          placeholder="Email"
          value={formData.email}
          onChange={handleInputChange}
          required
        />
        
        <Input
          type="password"
          name="password"
          placeholder="Password"
          value={formData.password}
          onChange={handleInputChange}
          required
          minLength="8"
        />
        
        <Button type="submit" disabled={loading}>
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin" style={{ marginRight: '0.5rem' }}></i>
              {isLogin ? 'Logging in...' : 'Creating account...'}
            </>
          ) : (
            <>
              <i className={`fas ${isLogin ? 'fa-sign-in-alt' : 'fa-user-plus'}`} style={{ marginRight: '0.5rem' }}></i>
              {isLogin ? 'Login' : 'Create Account'}
            </>
          )}
        </Button>
      </AuthForm>
      
      <div style={{ textAlign: 'center', marginTop: '1rem', color: 'rgba(255, 255, 255, 0.8)' }}>
        {isLogin ? "Don't have an account?" : "Already have an account?"}
        <SecondaryButton 
          type="button" 
          onClick={() => {
            setIsLogin(!isLogin);
            setError('');
            setSuccess('');
            setFormData({ email: '', password: '', fullName: '' });
          }}
          style={{ marginLeft: '0.5rem' }}
        >
          {isLogin ? 'Sign up' : 'Login'}
        </SecondaryButton>
      </div>
    </AuthContainer>
  );
};

export default AuthFormComponent; 