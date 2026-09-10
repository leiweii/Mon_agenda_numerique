import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Inscription from './Inscription';

const mockRegister = jest.fn();
const mockNavigate = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ register: mockRegister }),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}), { virtual: true });

beforeEach(() => {
  jest.clearAllMocks();
});

test('registers the user and redirects to the dashboard', async () => {
  mockRegister.mockResolvedValue({
    token: 'token',
    user: { id: 7, username: 'alice', email: 'alice@example.com' },
  });
  render(<Inscription />);

  fireEvent.change(screen.getByLabelText(/Nom d'utilisateur/), {
    target: { value: 'Alice' },
  });
  fireEvent.change(screen.getByLabelText(/^E-mail/), {
    target: { value: 'Alice@Example.COM' },
  });
  fireEvent.change(screen.getByLabelText(/^Mot de passe/), {
    target: { value: 'Une phrase de passe robuste 2026!' },
  });
  fireEvent.change(screen.getByLabelText(/Confirmer le mot de passe/), {
    target: { value: 'Une phrase de passe robuste 2026!' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));

  await waitFor(() => expect(mockRegister).toHaveBeenCalledWith({
    username: 'Alice',
    email: 'Alice@Example.COM',
    password: 'Une phrase de passe robuste 2026!',
  }));
  expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
});

test('shows an error when password confirmation does not match', async () => {
  render(<Inscription />);

  fireEvent.change(screen.getByLabelText(/Nom d'utilisateur/), {
    target: { value: 'alice' },
  });
  fireEvent.change(screen.getByLabelText(/^E-mail/), {
    target: { value: 'alice@example.com' },
  });
  fireEvent.change(screen.getByLabelText(/^Mot de passe/), {
    target: { value: 'Une phrase de passe robuste 2026!' },
  });
  fireEvent.change(screen.getByLabelText(/Confirmer le mot de passe/), {
    target: { value: 'mot de passe différent' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Créer mon compte' }));

  expect(await screen.findByText('Les mots de passe ne correspondent pas.')).toBeInTheDocument();
  expect(mockRegister).not.toHaveBeenCalled();
});
