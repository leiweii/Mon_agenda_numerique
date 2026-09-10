import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from './AuthContext';
import { authAPI } from '../services/api';

jest.mock('../services/api', () => ({
  authAPI: {
    getCurrentUser: jest.fn(),
    login: jest.fn(),
    logout: jest.fn(),
  },
}));

const USER = {
  id: 7,
  username: 'alice',
  email: 'alice@example.com',
};

const AuthState = () => {
  const { loading, user, logout } = useAuth();

  return (
    <>
      <span>{loading ? 'loading' : user?.username || 'guest'}</span>
      <button type="button" onClick={logout}>logout</button>
    </>
  );
};

const renderAuthState = () => render(
  <AuthProvider>
    <AuthState />
  </AuthProvider>
);

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
});

test('restores the current user from a stored token', async () => {
  localStorage.setItem('token', 'stored-token');
  authAPI.getCurrentUser.mockResolvedValue({ data: USER });

  renderAuthState();

  expect(await screen.findByText('alice')).toBeInTheDocument();
  expect(authAPI.getCurrentUser).toHaveBeenCalledTimes(1);
});

test('clears an invalid stored token when loading the current user fails', async () => {
  localStorage.setItem('token', 'invalid-token');
  authAPI.getCurrentUser.mockRejectedValue(new Error('Unauthorized'));

  renderAuthState();

  expect(await screen.findByText('guest')).toBeInTheDocument();
  expect(localStorage.getItem('token')).toBeNull();
});

test('revokes the remote token before clearing the local session', async () => {
  localStorage.setItem('token', 'stored-token');
  authAPI.getCurrentUser.mockResolvedValue({ data: USER });
  let resolveLogout;
  authAPI.logout.mockImplementation(() => new Promise((resolve) => {
    resolveLogout = resolve;
  }));

  renderAuthState();
  await screen.findByText('alice');
  fireEvent.click(screen.getByRole('button', { name: 'logout' }));

  await waitFor(() => expect(authAPI.logout).toHaveBeenCalledTimes(1));
  expect(localStorage.getItem('token')).toBe('stored-token');
  resolveLogout({ data: { message: 'Déconnexion réussie' } });

  expect(await screen.findByText('guest')).toBeInTheDocument();
  expect(localStorage.getItem('token')).toBeNull();
});
