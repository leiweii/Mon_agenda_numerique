import React from 'react';
import { render } from '@testing-library/react';
import Home from './Home';

jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Grid: ({ children, size }) => <div data-grid-size={JSON.stringify(size)}>{children}</div>,
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

jest.mock('react-router-dom', () => ({
  useNavigate: () => jest.fn(),
}), { virtual: true });

test('lays feature cards out in one, two, then four columns across MUI breakpoints', () => {
  const { container } = render(<Home />);

  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"sm\\":6,\\"md\\":3}"]')).toHaveLength(4);
});
