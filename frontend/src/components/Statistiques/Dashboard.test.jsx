import React from 'react';
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';
import { tachesAPI } from '../../services/api';

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
  tachesAPI.getMeilleurMoment.mockResolvedValue({ data: {} });
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
