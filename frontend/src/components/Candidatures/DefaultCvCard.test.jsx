import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import DefaultCvCard from './DefaultCvCard';
import { candidaturesAPI } from '../../services/api';

jest.mock('../../services/api', () => ({
  candidaturesAPI: { getDefaultCv: jest.fn(), replaceDefaultCv: jest.fn() },
}));

const pdf = (name = 'mon-cv.pdf') => new File(['%PDF-1.4\ncontent'], name, { type: 'application/pdf' });

beforeEach(() => {
  jest.clearAllMocks();
  candidaturesAPI.getDefaultCv.mockResolvedValue({ data: { filename: null } });
  candidaturesAPI.replaceDefaultCv.mockResolvedValue({ data: { filename: 'mon-cv.pdf' } });
});

test('shows missing CV and uploads the selected PDF', async () => {
  render(<DefaultCvCard />);

  expect(await screen.findByText('Aucun CV par défaut.')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Choisir un CV PDF'), { target: { files: [pdf()] } });
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter le CV' }));

  await waitFor(() => expect(candidaturesAPI.replaceDefaultCv).toHaveBeenCalledWith(expect.any(File)));
  expect(await screen.findByText('mon-cv.pdf')).toBeInTheDocument();
});

test('shows current filename and replaces it without a public download link', async () => {
  candidaturesAPI.getDefaultCv.mockResolvedValue({ data: { filename: 'ancien.pdf' } });
  candidaturesAPI.replaceDefaultCv.mockResolvedValue({ data: { filename: 'nouveau.pdf' } });
  render(<DefaultCvCard />);

  expect(await screen.findByText('ancien.pdf')).toBeInTheDocument();
  expect(screen.queryByRole('link', { name: 'ancien.pdf' })).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Choisir un CV PDF'), { target: { files: [pdf('nouveau.pdf')] } });
  fireEvent.click(screen.getByRole('button', { name: 'Remplacer le CV' }));

  expect(await screen.findByText('nouveau.pdf')).toBeInTheDocument();
});

test('rejects non-PDF selection before uploading', async () => {
  render(<DefaultCvCard />);
  await screen.findByText('Aucun CV par défaut.');

  fireEvent.change(screen.getByLabelText('Choisir un CV PDF'), {
    target: { files: [new File(['not pdf'], 'cv.txt', { type: 'text/plain' })] },
  });

  expect(screen.getByRole('alert')).toHaveTextContent('Sélectionnez un fichier PDF');
  expect(screen.getByRole('button', { name: 'Ajouter le CV' })).toBeDisabled();
  expect(candidaturesAPI.replaceDefaultCv).not.toHaveBeenCalled();
});

test('disables duplicate upload and keeps server error visible', async () => {
  let rejectUpload;
  candidaturesAPI.replaceDefaultCv.mockReturnValue(new Promise((_resolve, reject) => { rejectUpload = reject; }));
  render(<DefaultCvCard />);
  await screen.findByText('Aucun CV par défaut.');
  fireEvent.change(screen.getByLabelText('Choisir un CV PDF'), { target: { files: [pdf()] } });
  fireEvent.click(screen.getByRole('button', { name: 'Ajouter le CV' }));

  expect(screen.getByRole('button', { name: 'Téléversement...' })).toBeDisabled();
  rejectUpload({ response: { data: { detail: 'Fichier PDF invalide.' } } });
  expect(await screen.findByRole('alert')).toHaveTextContent('Fichier PDF invalide.');
  expect(screen.getByRole('button', { name: 'Ajouter le CV' })).toBeEnabled();
});
