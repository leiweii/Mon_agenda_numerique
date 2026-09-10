import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Login from './Login';

const mockLogin = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}), { virtual: true });

beforeEach(() => {
  jest.clearAllMocks();
});

test('submits credentials and redirects to the dashboard after login', async () => {
  mockLogin.mockResolvedValue({ token: 'token', user: { username: 'alice' } });
  render(<Login />);

  fireEvent.change(screen.getByLabelText(/Nom d'utilisateur/), {
    target: { value: 'alice' },
  });
  fireEvent.change(screen.getByLabelText(/Mot de passe/), {
    target: { value: 'secret-password' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

  await waitFor(() => expect(mockLogin).toHaveBeenCalledWith('alice', 'secret-password'));
  expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
});

test('displays an error when login is rejected', async () => {
  mockLogin.mockRejectedValue(new Error('Unauthorized'));
  render(<Login />);

  fireEvent.change(screen.getByLabelText(/Nom d'utilisateur/), {
    target: { value: 'alice' },
  });
  fireEvent.change(screen.getByLabelText(/Mot de passe/), {
    target: { value: 'wrong-password' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

  expect(await screen.findByText("Nom d'utilisateur ou mot de passe incorrect")).toBeInTheDocument();
  expect(mockNavigate).not.toHaveBeenCalled();
});
