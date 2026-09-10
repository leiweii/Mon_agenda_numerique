import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import CategorieListe from './CategorieListe';
import { categoriesAPI, tachesAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
  categoriesAPI: {
    getAll: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
  },
  tachesAPI: {
    getAll: jest.fn(),
  },
}));

jest.mock('./CategorieForm', () => () => null);

test('removes a deleted category from the list without deleting its task', async () => {
  const category = { id: 4, nom: 'Travail', couleur: '#3498db', emoji: '💼' };
  categoriesAPI.getAll
    .mockResolvedValueOnce({ data: [category] })
    .mockResolvedValueOnce({ data: [] });
  tachesAPI.getAll.mockResolvedValue({
    data: [{ id: 7, titre: 'Préparer la réunion', categorie: category.id }],
  });
  categoriesAPI.delete.mockResolvedValue();
  jest.spyOn(window, 'confirm').mockReturnValue(true);

  render(<CategorieListe />);

  expect(await screen.findByText('Travail')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Supprimer Travail' }));

  expect(await screen.findByText('Aucune catégorie créée')).toBeInTheDocument();
  expect(screen.queryByText('Travail')).not.toBeInTheDocument();
});
