import React from 'react';
import { render, screen } from '@testing-library/react';

import RecommandationsIA from './RecommandationsIA';
import { tachesAPI } from '../services/api';


jest.mock('../services/api', () => ({
  tachesAPI: {
    getRecommandationIA: jest.fn(),
  },
}));


beforeEach(() => {
  jest.clearAllMocks();
});


test('affiche un skeleton pendant le chargement de la recommandation', () => {
  tachesAPI.getRecommandationIA.mockReturnValue(new Promise(() => {}));

  render(<RecommandationsIA />);

  expect(screen.getByLabelText('Chargement de la recommandation IA')).toBeInTheDocument();
});


test('affiche les heures et le message de la recommandation IA', async () => {
  tachesAPI.getRecommandationIA.mockResolvedValue({
    data: {
      heures_recommandees: [9, 14],
      message: 'Commencez par votre tâche urgente.',
    },
  });

  render(<RecommandationsIA />);

  expect(await screen.findByText('Commencez par votre tâche urgente.')).toBeInTheDocument();
  expect(screen.getByText('Heures recommandées : 9h, 14h')).toBeInTheDocument();
});


test('affiche une erreur claire si la recommandation IA est indisponible', async () => {
  tachesAPI.getRecommandationIA.mockRejectedValue(new Error('network'));

  render(<RecommandationsIA />);

  expect(await screen.findByText('Impossible de charger la recommandation IA.')).toBeInTheDocument();
});
