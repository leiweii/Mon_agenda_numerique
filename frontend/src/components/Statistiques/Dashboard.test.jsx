import React from 'react';
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';
import { tachesAPI } from '../../services/api';

jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  Grid: ({ children, size }) => <div data-grid-size={JSON.stringify(size)}>{children}</div>,
}));

jest.mock('../../services/api', () => ({
  tachesAPI: {
    getStatistiques: jest.fn(),
    getMeilleurMoment: jest.fn(),
    getAujourdhui: jest.fn(),
    getCetteSemaine: jest.fn(),
  },
}));

jest.mock('./GraphiquesPriorite', () => ({ data }) => (
  <div>Graphique de priorité : {data.length} niveaux</div>
));

jest.mock('../RecommandationsIA', () => () => <div>Recommandation IA intégrée</div>);

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(console, 'error').mockImplementation(() => {});
  tachesAPI.getStatistiques.mockResolvedValue({
    data: {
      total: 4,
      completees: 2,
      en_cours: 2,
      taux_completion: 50,
      par_priorite: [
        { priorite: 1, count: 1 },
        { priorite: 2, count: 1 },
        { priorite: 3, count: 1 },
        { priorite: 4, count: 1 },
      ],
    },
  });
  tachesAPI.getAujourdhui.mockResolvedValue({ data: [] });
  tachesAPI.getCetteSemaine.mockResolvedValue({ data: [] });
});

afterEach(() => {
  console.error.mockRestore();
});

test('renders task totals, completion rate and normalized priority chart data', async () => {
  render(<Dashboard />);

  expect(await screen.findByText('Graphique de priorité : 4 niveaux')).toBeInTheDocument();
  expect(screen.getByText('50% de réussite')).toBeInTheDocument();
  expect(screen.getAllByText('2')).toHaveLength(2);
});

test('displays a clear error when statistics cannot be loaded', async () => {
  tachesAPI.getStatistiques.mockRejectedValue(new Error('Network error'));

  render(<Dashboard />);

  expect(await screen.findByText('Impossible de charger les statistiques.')).toBeInTheDocument();
});

test('uses MUI v7 breakpoint sizes for dashboard cards and panels', async () => {
  const { container } = render(<Dashboard />);

  await screen.findByText('Graphique de priorité : 4 niveaux');
  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"sm\\":6,\\"md\\":3}"]')).toHaveLength(4);
  expect(container.querySelectorAll('[data-grid-size="{\\"xs\\":12,\\"md\\":6}"]')).toHaveLength(2);
});

test('intègre le composant de recommandation IA au dashboard', async () => {
  render(<Dashboard />);

  expect(await screen.findByText('Recommandation IA intégrée')).toBeInTheDocument();
});
