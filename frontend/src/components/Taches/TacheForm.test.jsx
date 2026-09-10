import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import TacheForm from './TacheForm';

jest.mock('@mui/x-date-pickers/DateTimePicker', () => ({
  DateTimePicker: ({ label, value, onChange }) => (
    <input
      aria-label={label}
      type="datetime-local"
      value={value.toISOString().slice(0, 16)}
      onChange={(event) => onChange(new Date(event.target.value))}
    />
  ),
}));

jest.mock('@mui/x-date-pickers/LocalizationProvider', () => ({
  LocalizationProvider: ({ children }) => children,
}));

jest.mock('@mui/x-date-pickers/AdapterDateFns', () => ({
  AdapterDateFns: class AdapterDateFns {},
}));

jest.mock('date-fns/locale', () => ({ fr: {} }));

test('keeps the form open and displays an error when saving a task fails', async () => {
  const onSubmit = jest.fn().mockRejectedValue(new Error('Network error'));
  const onClose = jest.fn();

  render(
    <TacheForm
      open
      onClose={onClose}
      onSubmit={onSubmit}
      tache={null}
      categories={[]}
    />
  );

  fireEvent.change(screen.getByLabelText(/Titre/), {
    target: { value: 'Préparer la réunion' },
  });
  fireEvent.click(screen.getByRole('button', { name: 'Créer' }));

  expect(await screen.findByText("Impossible d'enregistrer la tâche.")).toBeInTheDocument();
  expect(onClose).not.toHaveBeenCalled();
});

test('submits the selected category identifier with a task', async () => {
  const onSubmit = jest.fn().mockResolvedValue();

  render(
    <TacheForm
      open
      onClose={jest.fn()}
      onSubmit={onSubmit}
      tache={null}
      categories={[{ id: 12, nom: 'Travail', emoji: '💼' }]}
    />
  );

  fireEvent.change(screen.getByLabelText(/Titre/), {
    target: { value: 'Préparer la réunion' },
  });
  fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Catégorie' }));
  fireEvent.click(screen.getByRole('option', { name: '💼 Travail' }));
  fireEvent.click(screen.getByRole('button', { name: 'Créer' }));

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ categorie: 12 }));
  });
});
