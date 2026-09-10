import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import MotDePasseOublie from './MotDePasseOublie';
import { authAPI } from '../services/api';

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}), { virtual: true });

jest.mock('../services/api', () => ({
  authAPI: { requestPasswordReset: jest.fn() },
}));

beforeEach(() => jest.clearAllMocks());

test('submits the email and shows the generic confirmation', async () => {
  authAPI.requestPasswordReset.mockResolvedValue({
    data: { message: 'Si ce compte existe, un e-mail a été envoyé.' },
  });
  render(<MotDePasseOublie />);

  fireEvent.change(screen.getByLabelText(/^E-mail/), { target: { value: 'alice@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }));

  await waitFor(() => expect(authAPI.requestPasswordReset).toHaveBeenCalledWith('alice@example.com'));
  expect(await screen.findByText('Si ce compte existe, un e-mail a été envoyé.')).toBeInTheDocument();
});

test('shows throttling details when the request is rejected', async () => {
  authAPI.requestPasswordReset.mockRejectedValue({ response: { data: { detail: 'Trop de demandes.' } } });
  render(<MotDePasseOublie />);

  fireEvent.change(screen.getByLabelText(/^E-mail/), { target: { value: 'alice@example.com' } });
  fireEvent.click(screen.getByRole('button', { name: 'Envoyer le lien' }));

  expect(await screen.findByText('Trop de demandes.')).toBeInTheDocument();
});
