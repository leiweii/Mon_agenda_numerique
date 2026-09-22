import React from 'react';
import { render, waitFor } from '@testing-library/react';
import Parametres from './Parametres';
import { gmailAPI, preferencesAPI } from '../services/api';

jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Grid: ({ children, size }) => <div data-grid-size={JSON.stringify(size)}>{children}</div>,
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { username: 'alice', email: 'alice@example.com' } }),
}));

jest.mock('../services/api', () => ({
  preferencesAPI: { get: jest.fn() },
  gmailAPI: { getStatus: jest.fn(), verify: jest.fn(), connect: jest.fn() },
}));

test('stacks settings on mobile and gives productive hours enough space from the small breakpoint', async () => {
  preferencesAPI.get.mockResolvedValue({ data: [] });
  gmailAPI.getStatus.mockResolvedValue({ data: { status: 'disconnected' } });
  const { container } = render(<Parametres onThemeChange={jest.fn()} />);

  await waitFor(() => expect(preferencesAPI.get).toHaveBeenCalledTimes(1));
  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"md\\":4}"]')).toHaveLength(1);
  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"md\\":8}"]')).toHaveLength(1);
  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"sm\\":6}"]')).toHaveLength(2);
});
