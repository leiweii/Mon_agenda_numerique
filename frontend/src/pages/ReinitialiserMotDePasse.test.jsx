import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import ReinitialiserMotDePasse from './ReinitialiserMotDePasse';
import { authAPI } from '../services/api';

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
  useParams: () => ({ uid: 'uid-test', token: 'token-test' }),
}), { virtual: true });

jest.mock('../services/api', () => ({
  authAPI: { resetPassword: jest.fn() },
}));

beforeEach(() => jest.clearAllMocks());

const renderPage = () => render(<ReinitialiserMotDePasse />);

test('submits a matching new password with route parameters', async () => {
  authAPI.resetPassword.mockResolvedValue({ data: { message: 'Mot de passe réinitialisé avec succès.' } });
  renderPage();

  fireEvent.change(screen.getByLabelText(/^Nouveau mot de passe/), {
    target: { value: 'Un nouveau mot de passe robuste 2026!' },
  });
  fireEvent.change(screen.getByLabelText(/Confirmer le mot de passe/), {
    target: { value: 'Un nouveau mot de passe robuste 2026!' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Réinitialiser le mot de passe' }));

  await waitFor(() => expect(authAPI.resetPassword).toHaveBeenCalledWith({
    uid: 'uid-test',
    token: 'token-test',
    password: 'Un nouveau mot de passe robuste 2026!',
    password_confirmation: 'Un nouveau mot de passe robuste 2026!',
  }));
  expect(await screen.findByText('Mot de passe réinitialisé avec succès.')).toBeInTheDocument();
});

test('does not submit mismatched passwords', async () => {
  renderPage();

  fireEvent.change(screen.getByLabelText(/^Nouveau mot de passe/), { target: { value: 'mot de passe un' } });
  fireEvent.change(screen.getByLabelText(/Confirmer le mot de passe/), { target: { value: 'mot de passe deux' } });
  fireEvent.click(screen.getByRole('button', { name: 'Réinitialiser le mot de passe' }));

  expect(await screen.findByText('Les mots de passe ne correspondent pas.')).toBeInTheDocument();
  expect(authAPI.resetPassword).not.toHaveBeenCalled();
});
