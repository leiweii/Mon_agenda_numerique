import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import EmailBrouillonDialog from './EmailBrouillonDialog';

const draft = {
  id: 12,
  recipient_email: 'recrutement@example.com',
  subject: 'Candidature spontanee',
  body: 'Bonjour Madame, Monsieur',
  status: 'draft',
};

test('edits recipient, subject and message before saving', () => {
  const onSave = jest.fn();
  render(<EmailBrouillonDialog open draft={draft} cvName="CV_backend.pdf" onSave={onSave} onCancel={jest.fn()} onSend={jest.fn()} />);
  const dialog = screen.getByRole('dialog', { name: 'Prévisualiser le brouillon' });

  fireEvent.change(within(dialog).getByRole('textbox', { name: 'Destinataire' }), { target: { value: 'rh@example.com' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: 'Objet' }), { target: { value: 'Alternance Django' } });
  fireEvent.change(within(dialog).getByRole('textbox', { name: 'Message' }), { target: { value: 'Bonjour, voici ma candidature.' } });
  expect(within(dialog).getByText('CV_backend.pdf')).toBeInTheDocument();
  fireEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

  expect(onSave).toHaveBeenCalledWith(12, {
    recipient_email: 'rh@example.com',
    subject: 'Alternance Django',
    body: 'Bonjour, voici ma candidature.',
  });
});

test('cancels the draft without saving or preparing a send', () => {
  const onSave = jest.fn();
  const onCancel = jest.fn();
  const onSend = jest.fn();
  render(<EmailBrouillonDialog open draft={draft} cvName="CV_backend.pdf" onSave={onSave} onCancel={onCancel} onSend={onSend} />);

  fireEvent.change(screen.getByRole('textbox', { name: 'Message' }), { target: { value: 'Texte abandonne' } });
  fireEvent.click(screen.getByRole('button', { name: 'Annuler' }));

  expect(onCancel).toHaveBeenCalledWith(12);
  expect(onSave).not.toHaveBeenCalled();
  expect(onSend).not.toHaveBeenCalled();
});

test('prepares send action with edited values and does not send itself', () => {
  const onSend = jest.fn();
  render(<EmailBrouillonDialog open draft={draft} cvName="CV_backend.pdf" onSave={jest.fn()} onCancel={jest.fn()} onSend={onSend} />);

  fireEvent.change(screen.getByRole('textbox', { name: 'Objet' }), { target: { value: 'Alternance React' } });
  fireEvent.click(screen.getByRole('button', { name: 'Préparer l’envoi' }));

  expect(onSend).toHaveBeenCalledWith(12, {
    recipient_email: 'recrutement@example.com',
    subject: 'Alternance React',
    body: 'Bonjour Madame, Monsieur',
  });
});
