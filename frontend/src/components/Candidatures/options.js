export const STATUTS = {
  a_postuler: { label: 'A postuler', color: 'default' },
  postule: { label: 'Postule', color: 'info' },
  entretien: { label: 'Entretien', color: 'warning' },
  refuse: { label: 'Refuse', color: 'error' },
  accepte: { label: 'Accepte', color: 'success' },
};

export const TYPES_POSTE = {
  stage: 'Stage', alternance: 'Alternance', cdi: 'CDI', cdd: 'CDD',
  freelance: 'Freelance', autre: 'Autre',
};

export const SOURCES_CANAL = {
  linkedin: 'LinkedIn', indeed: 'Indeed', welcome_jungle: 'Welcome to the Jungle',
  site_direct: "Site de l'entreprise", cooptation: 'Cooptation / reseau', autre: 'Autre',
};

export const MODES_TRAVAIL = {
  '': 'Non precise', sur_site: 'Sur site', hybride: 'Hybride',
  teletravail: 'Teletravail',
};

export const TYPES_ACTION = {
  envoyee: 'Candidature envoyee',
  relance: 'Relance',
  entretien_tel: 'Entretien telephonique',
  entretien_visio: 'Entretien visio',
  entretien_presentiel: 'Entretien presentiel',
  test_technique: 'Test technique',
  offre_recue: 'Offre recue',
  reponse_negative: 'Reponse negative',
  note: 'Note libre',
};

export const FORM_DEFAULTS = {
  url: '', titre: '', entreprise: '', lieu: '', mode_travail: '', description: '', type_poste: 'autre',
  statut: 'a_postuler', source_extraction: '', source_canal: 'autre', tags: [],
  favori: false, archive: false, cv_utilise: '', date_limite: '', date_relance: '', notes: '',
};
