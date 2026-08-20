import React, { useState } from 'react';
import styled from 'styled-components';
import { API_BASE_URL, AUTH_BASE_URL } from '../config';
import {
  Panel as Card,
  PrimaryAction as PrimaryButton,
  SecondaryAction as GhostButton,
} from './ui';

const Title = styled.h2`
  font-size: 1.25rem;
  margin-bottom: 0.35rem;
`;

const Intro = styled.p`
  margin-bottom: 0.9rem;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.9rem;
  line-height: 1.45;
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

const Message = styled.div`
  border-radius: 0.55rem;
  padding: 0.55rem 0.7rem;
  font-size: 0.9rem;
  border: 1px solid ${(props) => (props.$error ? 'rgba(248, 113, 113, 0.55)' : 'rgba(74, 222, 128, 0.55)')};
  background: ${(props) => (props.$error ? 'rgba(248, 113, 113, 0.12)' : 'rgba(74, 222, 128, 0.12)')};
  color: ${(props) => (props.$error ? '#fecaca' : '#bbf7d0')};
`;

const Hint = styled.div`
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.72);
  margin-top: 0.45rem;
`;

const AuthForm = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loadingHint, setLoadingHint] = useState('');
  const [formData, setFormData] = useState({
    fullName: '',
    email: '',
    password: '',
  });

  const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const onFieldChange = (event) => {
    const { name, value } = event.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setError('');
    setSuccess('');
  };

  const submit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setLoadingHint('');
    setError('');
    setSuccess('');

    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin
        ? { email: formData.email, password: formData.password }
        : { email: formData.email, password: formData.password, full_name: formData.fullName };

      const retryableStatuses = new Set([429, 502, 503, 504]);
      const baseUrls = Array.from(new Set([AUTH_BASE_URL, API_BASE_URL]));
      let response = null;
      const attemptsPerBase = 2;

      for (let baseIndex = 0; baseIndex < baseUrls.length; baseIndex += 1) {
        const baseUrl = baseUrls[baseIndex];
        for (let attempt = 1; attempt <= attemptsPerBase; attempt += 1) {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 45000);
          try {
            response = await fetch(`${baseUrl}${endpoint}`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
              signal: controller.signal,
            });
          } catch (requestError) {
            clearTimeout(timeoutId);
            const canRetry = attempt < attemptsPerBase;
            if (canRetry) {
              setLoadingHint('Auth service is waking up. This can take 20-40 seconds...');
              await wait(6000);
              continue;
            }
            response = null;
            break;
          }
          clearTimeout(timeoutId);

          if (response.ok) {
            break;
          }
          if (retryableStatuses.has(response.status) && attempt < attemptsPerBase) {
            setLoadingHint('Auth service is waking up. This can take 20-40 seconds...');
            await wait(6000);
            continue;
          }
          break;
        }

        const shouldTryNextBase =
          (!response || retryableStatuses.has(response.status)) &&
          baseIndex < baseUrls.length - 1;
        if (shouldTryNextBase) {
          setLoadingHint('Primary auth route is busy. Trying fallback route...');
          await wait(2000);
          continue;
        }
        break;
      }

      if (!response) {
        throw new Error('Auth service is unavailable right now. Please try again.');
      }

      const text = await response.text();
      let result = {};
      try {
        result = text ? JSON.parse(text) : {};
      } catch (parseError) {
        if (!response.ok && response.status === 429) {
          throw new Error('Auth service is still waking up. Please wait 30-60 seconds and try again.');
        }
        throw new Error(`Server error ${response.status}`);
      }

      if (!response.ok && response.status === 429) {
        throw new Error('Auth service is still waking up. Please wait 30-60 seconds and try again.');
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
      if (submitError.name === 'AbortError') {
        setError('Auth service took too long to respond. Please try again in 20-40 seconds.');
      } else {
        setError(submitError.message || 'Network error');
      }
    } finally {
      setLoadingHint('');
      setLoading(false);
    }
  };

  return (
    <Card>
      <Title>{isLogin ? 'Sign in' : 'Create account'}</Title>
      <Intro>
        {isLogin
          ? 'Continue to the converter and your EPUB library.'
          : 'Create a free account to convert and save EPUB books.'}
      </Intro>

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
          {loading ? 'Please wait...' : isLogin ? 'Sign in' : 'Create account'}
        </PrimaryButton>
        {loading && (
          <Hint>{loadingHint || 'Submitting your request...'}</Hint>
        )}
      </Form>

      <div style={{ marginTop: '0.8rem' }}>
        <GhostButton
          type="button"
          onClick={() => {
            setIsLogin((prev) => !prev);
            setError('');
            setSuccess('');
            setLoadingHint('');
            setFormData({ fullName: '', email: '', password: '' });
          }}
        >
          {isLogin ? 'New here? Create an account' : 'Already registered? Sign in'}
        </GhostButton>
      </div>
    </Card>
  );
};

export default AuthForm;
