import React from 'react';
import { Box, ButtonBase, Card, CardContent, Checkbox, Chip, IconButton, Stack, Tooltip, Typography } from '@mui/material';
import { DeleteOutline, EditOutlined, OpenInNew, PlaceOutlined, Star } from '@mui/icons-material';
import { differenceInCalendarDays, format, isValid, parseISO } from 'date-fns';
import { MODES_TRAVAIL, STATUTS, TYPES_POSTE } from './options';

const EMAIL_STATUS_LABELS = {
  draft: 'Brouillon', ready: 'Prêt à envoyer', sending: 'Envoi en cours',
  sent: 'Envoyé', failed: 'Échec de l’envoi', cancelled: 'Annulé',
};

function dateLabel(value) {
  const date = value ? parseISO(value) : null;
  return date && isValid(date) ? format(date, 'dd/MM/yyyy') : '';
}

export default function CandidatureCard({ candidature, onOpen, onEdit, onDelete, selected = false, onSelect, disabled = false }) {
  const status = STATUTS[candidature.statut] || STATUTS.a_postuler;
  const days = candidature.date_limite ? differenceInCalendarDays(parseISO(candidature.date_limite), new Date()) : null;
  const urgent = days !== null && days <= 7;
  return (
    <Card component="article" variant="outlined" sx={{ borderRadius: 2.5, minWidth: 0, borderColor: 'divider',
      transition: 'box-shadow 150ms ease', '&:hover': { boxShadow: 2 } }}>
      <CardContent sx={{ p: { xs: 2, sm: 2.5 }, '&:last-child': { pb: { xs: 2, sm: 2.5 } } }}>
        <Stack direction="row" spacing={1.5} alignItems="flex-start" justifyContent="space-between">
          {onSelect && <Checkbox checked={selected} onChange={event => onSelect(candidature, event.target.checked)}
            disabled={disabled} sx={{ p: 0.5, mt: 0.25 }} inputProps={{ 'aria-label': `Selectionner ${candidature.titre} - ${candidature.entreprise || 'Entreprise non renseignee'}` }} />}
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography sx={{ fontSize: '1.1rem', fontWeight: 700, overflowWrap: 'anywhere' }}>
              {candidature.entreprise || 'Entreprise non renseignee'}
            </Typography>
            <ButtonBase disabled={disabled} onClick={() => (onOpen || onEdit)(candidature)} sx={{ textAlign: 'left', justifyContent: 'flex-start', maxWidth: '100%' }}>
              <Typography component="h3" variant="h6" sx={{ fontSize: '1rem', fontWeight: 400, overflowWrap: 'anywhere' }}>{candidature.titre}</Typography>
            </ButtonBase>
          </Box>
          {candidature.favori && <Tooltip title="Favori"><Star fontSize="small" color="warning" aria-label="Favori" /></Tooltip>}
          <Stack direction="row" spacing={0.8} alignItems="center" sx={{ flexShrink: 0 }}>
            <Box aria-hidden="true" sx={{ width: 9, height: 9, borderRadius: '50%', bgcolor: status.color === 'default' ? 'text.secondary' : `${status.color}.main` }} />
            <Typography variant="body2" color="text.secondary">{status.label}</Typography>
          </Stack>
        </Stack>
        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1} alignItems="center" sx={{ mt: 1.25, color: 'text.secondary' }}>
          {candidature.lieu && <Stack direction="row" spacing={0.25} alignItems="center"><PlaceOutlined fontSize="small" /><Typography variant="body2">{candidature.lieu}</Typography></Stack>}
          {candidature.mode_travail && <Typography variant="body2">{MODES_TRAVAIL[candidature.mode_travail]}</Typography>}
          <Chip size="small" variant="outlined" label={TYPES_POSTE[candidature.type_poste] || 'Autre'} />
          {candidature.archive && <Chip size="small" label="Archivee" variant="outlined" />}
        </Stack>
        {!!candidature.tags?.length && <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5} sx={{ mt: 1.25 }}>
          {candidature.tags.map((tag, index) => <Chip key={`${tag}-${index}`} label={tag} size="small" variant="outlined" sx={{ maxWidth: '100%' }} />)}
        </Stack>}
        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1.5} sx={{ mt: 1.25 }}>
          {candidature.date_ajout && <Typography variant="caption" color="text.secondary">Ajoutee le {dateLabel(candidature.date_ajout)}</Typography>}
          {candidature.date_limite && <Typography variant="caption" color={urgent ? 'warning.main' : 'text.secondary'}>
            {days < 0 ? 'Echeance depassee' : 'Date limite'} : {dateLabel(candidature.date_limite)}
          </Typography>}
          {candidature.date_relance && <Typography variant="caption" color="text.secondary">Relance : {dateLabel(candidature.date_relance)}</Typography>}
        </Stack>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1} sx={{ mt: 1.5, pt: 1, borderTop: 1, borderColor: 'divider' }}>
          <Typography variant="body2" color="text.secondary">Email : {EMAIL_STATUS_LABELS[candidature.email_status] || 'À préparer'}</Typography>
          <Stack direction="row" spacing={0.5}>
          {/^(https?):\/\//i.test(candidature.url || '') && <Tooltip title="Voir l'annonce originale"><IconButton component="a" href={candidature.url} target="_blank" rel="noopener noreferrer" aria-label={`Voir l'annonce originale : ${candidature.titre}`}><OpenInNew fontSize="small" /></IconButton></Tooltip>}
          <Tooltip title="Modifier"><span><IconButton disabled={disabled} onClick={() => onEdit(candidature)} aria-label={`Modifier ${candidature.titre}`}><EditOutlined fontSize="small" /></IconButton></span></Tooltip>
          <Tooltip title="Supprimer"><span><IconButton disabled={disabled} onClick={() => onDelete(candidature)} aria-label={`Supprimer ${candidature.titre}`}><DeleteOutline fontSize="small" /></IconButton></span></Tooltip>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
