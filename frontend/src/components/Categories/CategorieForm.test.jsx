import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import CategorieForm from './CategorieForm';

test('keeps the category form open and displays an error when saving fails', async () => {
  const onSubmit = jest.fn().mockRejectedValue(new Error('Network error'));
  const onClose = jest.fn();

  render(
    <CategorieForm
      open
      onClose={onClose}
      onSubmit={onSubmit}
      categorie={null}
    />
  );

  fireEvent.change(screen.getByRole('textbox', { name: /Nom de la catégorie/ }), {
    target: { value: 'Travail' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Créer' }));

  expect(await screen.findByText("Impossible d'enregistrer la catégorie.")).toBeInTheDocument();
  expect(onClose).not.toHaveBeenCalled();
});
