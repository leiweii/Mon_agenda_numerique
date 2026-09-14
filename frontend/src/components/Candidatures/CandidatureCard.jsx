import React from 'react';
import { Box, ButtonBase, Card, CardContent, Chip, IconButton, Stack, Tooltip, Typography } from '@mui/material';
import { DeleteOutline, EditOutlined, OpenInNew, Star } from '@mui/icons-material';
import { differenceInCalendarDays, format, isValid, parseISO } from 'date-fns';
import { STATUTS, TYPES_POSTE } from './options';

function dateLabel(value) {
  const date = value ? parseISO(value) : null;
  return date && isValid(date) ? format(date, 'dd/MM/yyyy') : '';
}

export default function CandidatureCard({ candidature, onOpen, onEdit, onDelete, disabled = false }) {
  const status = STATUTS[candidature.statut] || STATUTS.a_postuler;
  const days = candidature.date_limite ? differenceInCalendarDays(parseISO(candidature.date_limite), new Date()) : null;
  const urgent = days !== null && days <= 7;
  return (
    <Card component="article" variant="outlined" sx={{ borderRadius: '8px', minWidth: 0, height: '100%', borderLeftWidth: 3, borderLeftColor: urgent ? 'warning.main' : 'divider' }}>
      <CardContent>
        <Stack direction="row" spacing={1} alignItems="flex-start" justifyContent="space-between">
          <Box sx={{ minWidth: 0 }}>
            <ButtonBase disabled={disabled} onClick={() => (onOpen || onEdit)(candidature)} sx={{ textAlign: 'left', justifyContent: 'flex-start', maxWidth: '100%' }}>
              <Typography component="h3" variant="h6" sx={{ fontSize: '1rem', overflowWrap: 'anywhere' }}>{candidature.titre}</Typography>
            </ButtonBase>
            <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: 'anywhere' }}>{candidature.entreprise || 'Entreprise non renseignee'}</Typography>
          </Box>
          {candidature.favori && <Tooltip title="Favori"><Star fontSize="small" color="warning" aria-label="Favori" /></Tooltip>}
        </Stack>
        <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1} sx={{ my: 2 }}>
          <Chip size="small" label={status.label} color={status.color} />
          <Chip size="small" variant="outlined" label={TYPES_POSTE[candidature.type_poste] || 'Autre'} />
          {candidature.archive && <Chip size="small" label="Archivee" variant="outlined" />}
        </Stack>
        {!!candidature.tags?.length && <Stack direction="row" useFlexGap flexWrap="wrap" spacing={0.5} sx={{ mb: 2 }}>
          {candidature.tags.map((tag, index) => <Chip key={`${tag}-${index}`} label={tag} size="small" variant="outlined" sx={{ maxWidth: '100%' }} />)}
        </Stack>}
        {candidature.date_ajout && <Typography variant="caption" display="block" color="text.secondary">Ajoutee le {dateLabel(candidature.date_ajout)}</Typography>}
        {candidature.date_limite && <Typography variant="body2" color={urgent ? 'warning.main' : 'text.secondary'}>
          {days < 0 ? 'Echeance depassee' : 'Date limite'} : {dateLabel(candidature.date_limite)}
        </Typography>}
        {candidature.date_relance && <Typography variant="body2" color="text.secondary">Relance : {dateLabel(candidature.date_relance)}</Typography>}
        <Stack direction="row" justifyContent="flex-end" spacing={0.5} sx={{ mt: 1 }}>
          {/^(https?):\/\//i.test(candidature.url || '') && <Tooltip title="Voir l'annonce originale"><IconButton component="a" href={candidature.url} target="_blank" rel="noopener noreferrer" aria-label={`Voir l'annonce originale : ${candidature.titre}`}><OpenInNew fontSize="small" /></IconButton></Tooltip>}
          <Tooltip title="Modifier"><span><IconButton disabled={disabled} onClick={() => onEdit(candidature)} aria-label={`Modifier ${candidature.titre}`}><EditOutlined fontSize="small" /></IconButton></span></Tooltip>
          <Tooltip title="Supprimer"><span><IconButton disabled={disabled} onClick={() => onDelete(candidature)} aria-label={`Supprimer ${candidature.titre}`}><DeleteOutline fontSize="small" /></IconButton></span></Tooltip>
        </Stack>
      </CardContent>
    </Card>
  );
}
