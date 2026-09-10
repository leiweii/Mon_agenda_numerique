import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import TacheListe from './TacheListe';
import { categoriesAPI, tachesAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
  categoriesAPI: {
    getAll: jest.fn(),
  },
  tachesAPI: {
    getAll: jest.fn(),
    getAujourdhui: jest.fn(),
    getCetteSemaine: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock('./TacheCard', () => ({ tache }) => <div>{tache.titre}</div>);
jest.mock('./TacheForm', () => () => null);

const task = (id, titre, completee = false) => ({ id, titre, completee });

beforeEach(() => {
  jest.clearAllMocks();
  categoriesAPI.getAll.mockResolvedValue({ data: [] });
  tachesAPI.getAll.mockResolvedValue({ data: [task(1, 'Tâche sans filtre')] });
});

test('renders the tasks due today after selecting Aujourd hui', async () => {
  tachesAPI.getAujourdhui.mockResolvedValue({ data: [task(2, 'Tâche du jour')] });

  render(<TacheListe />);

  expect(await screen.findByText('Tâche sans filtre')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: "Aujourd'hui" }));

  expect(await screen.findByText('Tâche du jour')).toBeInTheDocument();
  expect(screen.queryByText('Tâche sans filtre')).not.toBeInTheDocument();
});

test('renders the tasks due this week after selecting Cette semaine', async () => {
  tachesAPI.getCetteSemaine.mockResolvedValue({ data: [task(3, 'Tâche de la semaine')] });

  render(<TacheListe />);

  expect(await screen.findByText('Tâche sans filtre')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Cette semaine' }));

  expect(await screen.findByText('Tâche de la semaine')).toBeInTheDocument();
  expect(screen.queryByText('Tâche sans filtre')).not.toBeInTheDocument();
});
