import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';
import { preferencesAPI } from './services/api';

jest.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }) => children,
  Routes: ({ children }) => children,
  Route: ({ element }) => element,
  Navigate: () => <div />,
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: '/' }),
  useParams: () => ({}),
}), { virtual: true });

jest.mock('./context/AuthContext', () => ({
  AuthProvider: ({ children }) => children,
  useAuth: () => ({ user: { username: 'alice' }, loading: false }),
}));

jest.mock('./services/api', () => ({
  preferencesAPI: { get: jest.fn() },
}));

jest.mock('./components/Layout/Navbar', () => () => <div />);
jest.mock('./components/Statistiques/Dashboard', () => () => <div />);
jest.mock('./components/Taches/TacheListe', () => () => <div />);
jest.mock('./components/Categories/CategorieListe', () => () => <div />);
jest.mock('./pages/Parametres', () => () => <div />);
jest.mock('./pages/Login', () => () => <div />);
jest.mock('./pages/Home', () => () => <div />);
jest.mock('./pages/Candidatures', () => () => <div />);
jest.mock('./pages/CandidatureDetail', () => () => <div />);
jest.mock('./components/Agent/AgentChat', () => () => <div />);

afterEach(() => {
  document.documentElement.removeAttribute('data-theme');
});

test('loads the saved dark theme when the authenticated app starts', async () => {
  preferencesAPI.get.mockResolvedValue({ data: [{ theme: 'sombre' }] });

  render(<App />);

  await waitFor(
    () => expect(document.documentElement).toHaveAttribute('data-theme', 'sombre'),
    { timeout: 5000 },
  );
});

test('shows Candidatures in the main navigation', () => {
  preferencesAPI.get.mockResolvedValue({ data: [] });
  render(<App />);
  expect(screen.getAllByText('Candidatures').length).toBeGreaterThan(0);
});

test('shows Assistant in the main navigation', () => {
  preferencesAPI.get.mockResolvedValue({ data: [] });
  render(<App />);
  expect(screen.getAllByText('Assistant').length).toBeGreaterThan(0);
});
