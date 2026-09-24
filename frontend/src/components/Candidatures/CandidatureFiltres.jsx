import React, { useId } from 'react';
import {
  Autocomplete, Box, Button, Checkbox, FormControl, FormControlLabel,
  Grid, InputLabel, ListItemText, MenuItem, Select, Stack, Switch, TextField,
} from '@mui/material';
import { ClearAll, Download, FilterAltOutlined } from '@mui/icons-material';
import { SOURCES_CANAL, STATUTS, TYPES_POSTE } from './options';

export const DEFAULT_FILTERS = {
  search: '', statut: [], type_poste: [], source_canal: [], tags: [],
  favori: false, archive: false, date_ajout_min: '', date_ajout_max: '',
  date_limite: false, relance_due: false, ordering: '-date_ajout',
};

const ORDERINGS = {
  '-date_ajout': "Ajout : plus recent",
  date_ajout: "Ajout : plus ancien",
  date_limite: 'Date limite : plus proche',
  date_relance: 'Date de relance : plus proche',
  statut: 'Statut',
};

function MultiSelect({ label, value, options, onChange }) {
  const id = useId();
  return (
    <FormControl fullWidth size="small">
      <InputLabel id={`${id}-label`}>{label}</InputLabel>
      <Select id={id} labelId={`${id}-label`} multiple label={label} value={value} onChange={event => onChange(event.target.value)}
        renderValue={selected => selected.map(item => options[item]?.label || options[item]).join(', ')}>
        {Object.entries(options).map(([key, option]) => (
          <MenuItem key={key} value={key}>
            <Checkbox checked={value.includes(key)} />
            <ListItemText primary={option.label || option} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
}

export default function CandidatureFiltres({ filters, onChange, tagsDisponibles, onExport, exporting = false, hideSearch = false }) {
  const orderingId = useId();
  const update = patch => onChange({ ...filters, ...patch });
  const active = JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS);
  const tagOptions = [...new Set([...tagsDisponibles, ...filters.tags])].sort();

  return (
    <Box component="section" aria-label="Filtres des candidatures" sx={{ py: 2.5, borderBottom: 1, borderColor: 'divider' }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} alignItems={{ xs: 'stretch', sm: 'center' }}
        justifyContent="space-between" spacing={1} sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><FilterAltOutlined color="action" /> Filtres</Box>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
          {onExport && <Button size="small" variant="outlined" startIcon={<Download />} disabled={exporting} onClick={onExport}>
            {exporting ? 'Export...' : 'Exporter en CSV'}
          </Button>}
          <Button size="small" startIcon={<ClearAll />} disabled={!active} onClick={() => onChange(DEFAULT_FILTERS)}>
            Effacer les filtres
          </Button>
        </Stack>
      </Stack>
      <Grid container spacing={1.5}>
        {!hideSearch && <Grid size={{ xs: 12, md: 4 }}>
          <TextField fullWidth size="small" label="Recherche" value={filters.search}
            onChange={event => update({ search: event.target.value })} />
        </Grid>}
        <Grid size={{ xs: 12, sm: 6, md: 4 }}><MultiSelect label="Statut" value={filters.statut} options={STATUTS} onChange={statut => update({ statut })} /></Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}><MultiSelect label="Type de poste" value={filters.type_poste} options={TYPES_POSTE} onChange={type_poste => update({ type_poste })} /></Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}><MultiSelect label="Source du canal" value={filters.source_canal} options={SOURCES_CANAL} onChange={source_canal => update({ source_canal })} /></Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <Autocomplete multiple options={tagOptions} value={filters.tags} onChange={(_, tags) => update({ tags })}
            renderInput={params => <TextField {...params} size="small" label="Tags" />} />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <FormControl fullWidth size="small">
            <InputLabel id={`${orderingId}-label`}>Tri</InputLabel>
            <Select id={orderingId} labelId={`${orderingId}-label`} label="Tri" value={filters.ordering} onChange={event => update({ ordering: event.target.value })}>
              {Object.entries(ORDERINGS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <TextField fullWidth size="small" type="date" label="Date d'ajout minimale" value={filters.date_ajout_min}
            onChange={event => update({ date_ajout_min: event.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <TextField fullWidth size="small" type="date" label="Date d'ajout maximale" value={filters.date_ajout_max}
            onChange={event => update({ date_ajout_max: event.target.value })} slotProps={{ inputLabel: { shrink: true } }} />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} useFlexGap flexWrap="wrap">
            <FormControlLabel label="Favoris uniquement" control={<Switch checked={filters.favori} onChange={event => update({ favori: event.target.checked })} />} />
            <FormControlLabel label="Inclure les archivees" control={<Switch checked={filters.archive} onChange={event => update({ archive: event.target.checked })} />} />
            <FormControlLabel label="Echeance sous 7 jours" control={<Checkbox checked={filters.date_limite} onChange={event => update({ date_limite: event.target.checked })} />} />
            <FormControlLabel label="A relancer" control={<Checkbox checked={filters.relance_due} onChange={event => update({ relance_due: event.target.checked })} />} />
          </Stack>
        </Grid>
      </Grid>
    </Box>
  );
}
