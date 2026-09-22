import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import GmailConnectionCard from './GmailConnectionCard';
import { gmailAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
  gmailAPI: {
    getStatus: jest.fn(),
    verify: jest.fn(),
    connect: jest.fn(),
  },
}));

beforeEach(() => {
  jest.resetAllMocks();
  gmailAPI.getStatus.mockResolvedValue({ data: { status: 'disconnected' } });
});

test('offers connection and navigates only to the authorization URL returned by backend', async () => {
  const navigateToOAuth = jest.fn();
  gmailAPI.connect.mockResolvedValue({ data: { authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=abc' } });
  render(<GmailConnectionCard navigateToOAuth={navigateToOAuth} />);

  fireEvent.click(await screen.findByRole('button', { name: 'Connecter mon compte Gmail' }));

  await waitFor(() => expect(navigateToOAuth).toHaveBeenCalledWith('https://accounts.google.com/o/oauth2/v2/auth?state=abc'));
  expect(screen.queryByText(/refresh.token/i)).not.toBeInTheDocument();
});

test('shows reconnection when the stored token has been revoked', async () => {
  gmailAPI.getStatus.mockResolvedValue({ data: { status: 'connected' } });
  gmailAPI.verify.mockResolvedValue({ data: { status: 'reconnect_required', message: 'Reconnectez votre compte Gmail pour continuer.' } });
  render(<GmailConnectionCard navigateToOAuth={jest.fn()} />);

  expect(await screen.findByText('Reconnectez votre compte Gmail pour continuer.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Reconnecter mon compte Gmail' })).toBeInTheDocument();
});

test('keeps connection status on a temporary verification failure', async () => {
  gmailAPI.getStatus.mockResolvedValue({ data: { status: 'connected' } });
  gmailAPI.verify.mockRejectedValue({ response: { data: { detail: 'Verification Gmail momentanement indisponible. Reessayez plus tard.' } } });
  render(<GmailConnectionCard navigateToOAuth={jest.fn()} />);

  expect(await screen.findByText('Verification Gmail momentanement indisponible. Reessayez plus tard.')).toBeInTheDocument();
  expect(screen.getByText('Compte Gmail connecté')).toBeInTheDocument();
});

test('disables the connect button while requesting the Google URL', async () => {
  let finish;
  gmailAPI.connect.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  render(<GmailConnectionCard navigateToOAuth={jest.fn()} />);

  const button = await screen.findByRole('button', { name: 'Connecter mon compte Gmail' });
  fireEvent.click(button);
  expect(button).toBeDisabled();
  finish({ data: { authorization_url: 'https://accounts.google.com/' } });
  await waitFor(() => expect(button).not.toBeDisabled());
});

test('shows a clear error after an unsuccessful Google callback', async () => {
  window.history.pushState({}, '', '/parametres?gmail=error');
  try {
    render(<GmailConnectionCard navigateToOAuth={jest.fn()} />);
    expect(await screen.findByText('La connexion Gmail n’a pas abouti. Réessayez.')).toBeInTheDocument();
  } finally {
    window.history.pushState({}, '', '/');
  }
});
