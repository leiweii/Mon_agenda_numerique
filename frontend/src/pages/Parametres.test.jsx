import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import Parametres from './Parametres';
import { gmailAPI, preferencesAPI } from '../services/api';

const onThemeChange = jest.fn();

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'alice', email: 'alice@example.com' } }),
}));

jest.mock('../services/api', () => ({
  preferencesAPI: {
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
  },
  gmailAPI: { getStatus: jest.fn(), verify: jest.fn(), connect: jest.fn() },
}));

beforeEach(() => {
  jest.clearAllMocks();
  preferencesAPI.get.mockResolvedValue({ data: [] });
  gmailAPI.getStatus.mockResolvedValue({ data: { status: 'disconnected' } });
  preferencesAPI.create.mockResolvedValue({
    data: {
      id: 7,
      heure_productive_debut: '09:00:00',
      heure_productive_fin: '17:00:00',
      theme: 'sombre',
      notifications_actives: false,
    },
  });
});

test('creates preferences and applies the selected theme after saving', async () => {
  render(<Parametres onThemeChange={onThemeChange} />);

  await waitFor(() => expect(preferencesAPI.get).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByDisplayValue('clair'), { target: { value: 'sombre' } });
  fireEvent.click(screen.getByRole('switch'));
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

  await waitFor(() => expect(preferencesAPI.create).toHaveBeenCalledWith(expect.objectContaining({
    theme: 'sombre',
    notifications_actives: false,
  })));
  expect(onThemeChange).toHaveBeenCalledWith('sombre');
  expect(await screen.findByText('Paramètres sauvegardés avec succès !')).toBeInTheDocument();
});

test('updates existing preferences instead of creating a second record', async () => {
  preferencesAPI.get.mockResolvedValue({
    data: [{
      id: 7,
      heure_productive_debut: '09:00:00',
      heure_productive_fin: '17:00:00',
      theme: 'sombre',
      notifications_actives: true,
    }],
  });
  preferencesAPI.update.mockResolvedValue({
    data: {
      id: 7,
      heure_productive_debut: '09:00:00',
      heure_productive_fin: '17:00:00',
      theme: 'clair',
      notifications_actives: true,
    },
  });

  render(<Parametres onThemeChange={onThemeChange} />);

  await waitFor(() => expect(screen.getByDisplayValue('sombre')).toBeInTheDocument());
  fireEvent.change(screen.getByDisplayValue('sombre'), { target: { value: 'clair' } });
  fireEvent.click(screen.getByRole('button', { name: 'Enregistrer les modifications' }));

  await waitFor(() => expect(preferencesAPI.update).toHaveBeenCalledWith(7, expect.objectContaining({
    theme: 'clair',
  })));
  expect(preferencesAPI.create).not.toHaveBeenCalled();
  expect(onThemeChange).toHaveBeenCalledWith('clair');
});
