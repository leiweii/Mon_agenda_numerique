import axios from 'axios';
import { candidaturesAPI } from './api';

jest.mock('axios', () => {
  const client = {
    put: jest.fn(),
    interceptors: { request: { use: jest.fn() } },
  };
  return { create: jest.fn(() => client), client };
});

test('CV upload sends a multipart PUT to the candidature default-CV route', () => {
  const file = new File(['%PDF-1.4\nvalid'], 'cv.pdf', { type: 'application/pdf' });

  candidaturesAPI.replaceDefaultCv(file);

  expect(axios.client.put).toHaveBeenCalledWith(
    'candidatures/cv_par_defaut/',
    expect.any(FormData),
    { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  const sent = axios.client.put.mock.calls[0][1];
  expect(sent.get('fichier')).toBe(file);
});
