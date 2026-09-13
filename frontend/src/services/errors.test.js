import { extraireMessageErreur } from './errors';

test.each([
  [{ response: { data: { error: 'Erreur métier' } } }, 'Erreur métier'],
  [{ response: { data: { detail: 'Trop de tentatives' } } }, 'Trop de tentatives'],
  [{ response: { data: { non_field_errors: ['Donnée invalide'] } } }, 'Donnée invalide'],
  [new Error('Erreur réseau'), 'Fallback'],
])('extracts the API error message', (error, expected) => {
  expect(extraireMessageErreur(error, 'Fallback')).toBe(expected);
});
