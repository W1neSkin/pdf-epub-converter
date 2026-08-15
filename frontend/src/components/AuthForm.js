import React, { useState } from 'react';
import styled from 'styled-components';
import { API_BASE_URL } from '../config';

const Card = styled.div`
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 0.9rem;
  padding: 1.2rem;
`;

const Title = styled.h2`
  font-size: 1.25rem;
  margin-bottom: 0.9rem;
`;

const Form = styled.form`
  display: grid;
  gap: 0.7rem;
`;

const Label = styled.label`
  font-size: 0.86rem;
  color: rgba(255, 255, 255, 0.84);
`;

const Input = styled.input`
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 0.6rem;
  background: rgba(255, 255, 255, 0.08);
  color: white;
  padding: 0.7rem 0.8rem;
`;

const Row = styled.div`
  display: grid;
  gap: 0.4rem;
`;

const PrimaryButton = styled.button`
  margin-top: 0.3rem;
  border: none;
  border-radius: 0.6rem;
  background: #facc15;
  color: #111827;
  font-weight: 700;
  min-height: 2.5rem;
  cursor: pointer;
`;

const GhostButton = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 0.6rem;
  background: transparent;
  color: white;
  min-height: 2.4rem;
  cursor: pointer;
  font-weight: 600;
`;

const Message = styled.div`
  border-radius: 0.55rem;
  padding: 0.55rem 0.7rem;
  font-size: 0.9rem;
  border: 1px solid ${(props) => (props.$error ? 'rgba(248, 113, 113, 0.55)' : 'rgba(74, 222, 128, 0.55)')};
  background: ${(props) => (props.$error ? 'rgba(248, 113, 113, 0.12)' : 'rgba(74, 222, 128, 0.12)')};
  color: ${(props) => (props.$error ? '#fecaca' : '#bbf7d0')};
`;

const AuthForm = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
  });

  const onFieldChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
    setSuccess('');
  };

  const submit = async (event) => {
    event.preventDefault();
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const text = await response.text();
      let result = {};
      try {
        result = text ? JSON.parse(text) : {};
      } catch (parseError) {
        throw new Error(`Server error ${response.status}`);
      }

      if (!result.success) {
        throw new Error(result.message || result.detail || 'Authentication failed');
      }

      if (isLogin) {
        const userData = {
          token: result.data.access_token,
          user_id: result.data.user_id,
          email: formData.email,
        };
        localStorage.setItem('authToken', result.data.access_token);
        localStorage.setItem('userData', JSON.stringify(userData));
        setSuccess('Login successful.');
        setTimeout(() => onAuthSuccess(userData), 250);
      } else {
        setSuccess('Account created. Please log in.');
        setIsLogin(true);
        setFormData((prev) => ({ ...prev, password: '' }));
      }
    } catch (submitError) {
      setError(submitError.message || 'Network error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <Title>{isLogin ? 'Login' : 'Create account'}</Title>

      {error && <Message $error>{error}</Message>}
      {success && <Message>{success}</Message>}

      <Form onSubmit={submit}>
        {!isLogin && (
          <Row>
            <Label htmlFor="fullName">Full name</Label>
            <Input
              id="fullName"
              name="fullName"
              value={formData.fullName}
              onChange={onFieldChange}
              required
            />
          </Row>
        )}

        <Row>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            name="email"
            type="email"
            value={formData.email}
            onChange={onFieldChange}
            required
          />
        </Row>

        <Row>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            name="password"
            type="password"
            minLength={8}
            value={formData.password}
            onChange={onFieldChange}
            required
          />
        </Row>

        <PrimaryButton type="submit" disabled={loading}>
          {loading ? 'Please wait...' : isLogin ? 'Login' : 'Create account'}
        </PrimaryButton>
      </Form>

      <div style={{ marginTop: '0.8rem' }}>
        <GhostButton
          type="button"
          onClick={() => {
            setIsLogin((prev) => !prev);
            setError('');
            setSuccess('');
            setFormData({ fullName: '', email: '', password: '' });
          }}
        >
          {isLogin ? 'Need an account? Sign up' : 'Already registered? Login'}
        </GhostButton>
      </div>
    </Card>
  );
};

export default AuthForm;
