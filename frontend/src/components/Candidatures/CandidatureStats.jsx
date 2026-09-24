import React from 'react';
import { Box, ButtonBase, Grid, Typography } from '@mui/material';

export function countCandidatureStats(candidatures, today) {
  const inSevenDays = new Date(`${today}T00:00:00Z`);
  inSevenDays.setUTCDate(inSevenDays.getUTCDate() + 7);
  const lastDay = inSevenDays.toISOString().slice(0, 10);

  return candidatures.reduce((counts, candidature) => {
    if (['postule', 'entretien'].includes(candidature.statut)) counts.enCours += 1;
    // Garder exactement la semantique actuelle du filtre backend relance_due.
    if (candidature.date_relance && candidature.date_relance <= today) counts.aRelancer += 1;
    if (candidature.date_limite && candidature.date_limite >= today && candidature.date_limite <= lastDay) counts.echeance += 1;
    return counts;
  }, { enCours: 0, aRelancer: 0, echeance: 0 });
}

export default function CandidatureStats({ candidatures, today, onRelance }) {
  const counts = countCandidatureStats(candidatures, today);
  const stats = [
    { label: 'En cours', value: counts.enCours },
    { label: 'À relancer', value: counts.aRelancer, highlight: true },
    { label: 'Échéance sous 7 jours', value: counts.echeance },
  ];

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {stats.map(({ label, value, highlight }) => <Grid key={label} size={{ xs: 12, sm: 4 }}>
        <Box component={highlight ? ButtonBase : 'div'} onClick={highlight ? onRelance : undefined}
          aria-label={highlight ? `${label} : ${value}` : undefined}
          sx={{ width: '100%', minHeight: 112, borderRadius: 2.5, border: 1,
            borderColor: highlight ? 'warning.main' : 'divider',
            bgcolor: theme => highlight ? (theme.palette.mode === 'dark' ? theme.palette.warning.dark : theme.palette.warning.light) : theme.palette.background.paper,
            color: 'text.primary', display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center', textAlign: 'center', px: 2, py: 1.5 }}>
          <Typography component="strong" sx={{ fontSize: '2rem', lineHeight: 1.15, fontWeight: 700 }}>{value}</Typography>
          <Typography variant="body1">{label}</Typography>
        </Box>
      </Grid>)}
    </Grid>
  );
}
