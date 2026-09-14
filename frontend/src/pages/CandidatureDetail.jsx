import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert, Autocomplete, Box, Button, Chip, CircularProgress, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl,
  Grid, IconButton, InputLabel, Link, MenuItem, Select, Stack, TextField,
  Tooltip, Typography,
} from '@mui/material';
import {
  ArchiveOutlined, ArrowBack, DeleteOutline, EditOutlined, OpenInNew,
  Save, Star, StarBorder,
} from '@mui/icons-material';
import { format, isValid, parseISO } from 'date-fns';
import ActionForm from '../components/Candidatures/ActionForm';
import ActionTimeline from '../components/Candidatures/ActionTimeline';
import CandidatureForm from '../components/Candidatures/CandidatureForm';
import { MODES_TRAVAIL, SOURCES_CANAL, STATUTS, TYPES_POSTE } from '../components/Candidatures/options';
import { candidatureActionsAPI, candidaturesAPI } from '../services/api';
import { extraireMessageErreur } from '../services/errors';

function dateLabel(value, withTime = false) {
  const parsed = value ? parseISO(value) : null;
  return parsed && isValid(parsed) ? format(parsed, withTime ? 'dd/MM/yyyy HH:mm' : 'dd/MM/yyyy') : 'Non renseignee';
}

function Info({ label, children }) {
  return <Box><Typography variant="caption" color="text.secondary">{label}</Typography><Typography sx={{ overflowWrap: 'anywhere' }}>{children || 'Non renseigne'}</Typography></Box>;
}

export default function CandidatureDetail() {
  const { id } = useParams();
  const candidatureId = Number(id);
  const navigate = useNavigate();
  const [candidature, setCandidature] = useState(null);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editorOpen, setEditorOpen] = useState(false);
  const [actionEditor, setActionEditor] = useState(undefined);
  const [confirmation, setConfirmation] = useState('');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');

  const applyCandidature = data => {
    setCandidature(data);
    setTags(data.tags || []);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [candidatureResponse, actionsResponse] = await Promise.all([
        candidaturesAPI.getById(candidatureId),
        candidatureActionsAPI.getAll(candidatureId),
      ]);
      applyCandidature(candidatureResponse.data);
      setActions(actionsResponse.data);
    } catch (failure) {
      setError(extraireMessageErreur(failure, 'Impossible de charger cette candidature.'));
    } finally {
      setLoading(false);
    }
  }, [candidatureId]);

  useEffect(() => { load(); }, [load]);

  const patchCandidature = async data => {
    setBusy(true);
    setError('');
    try {
      const response = await candidaturesAPI.patch(candidatureId, data);
      applyCandidature(response.data);
    } catch (failure) {
      setError(extraireMessageErreur(failure, 'Impossible de modifier la candidature.'));
    } finally {
      setBusy(false);
    }
  };

  const saveGeneral = async data => {
    const response = await candidaturesAPI.update(candidatureId, data);
    applyCandidature(response.data);
  };

  const saveAction = async data => {
    const response = actionEditor
      ? await candidatureActionsAPI.update(candidatureId, actionEditor.id, data)
      : await candidatureActionsAPI.create(candidatureId, data);
    setActions(current => actionEditor
      ? current.map(item => item.id === response.data.id ? response.data : item)
      : [response.data, ...current]);
  };

  const deleteAction = async item => {
    if (!window.confirm('Supprimer cette action ?')) return;
    await candidatureActionsAPI.delete(candidatureId, item.id);
    setActions(current => current.filter(action => action.id !== item.id));
  };

  const confirm = async () => {
    setBusy(true);
    setError('');
    try {
      if (confirmation === 'archive') {
        const response = await candidaturesAPI.archive(candidatureId);
        applyCandidature(response.data);
        setConfirmation('');
      } else {
        await candidaturesAPI.delete(candidatureId);
        navigate('/candidatures');
      }
    } catch (failure) {
      setError(extraireMessageErreur(failure, "L'action n'a pas pu etre effectuee."));
      setConfirmation('');
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Box role="status" aria-label="Chargement de la candidature" sx={{ py: 8, textAlign: 'center' }}><CircularProgress /></Box>;
  if (!candidature) return <Alert severity="error" action={<Button onClick={load}>Reessayer</Button>}>{error || 'Candidature introuvable.'}</Alert>;

  return (
    <Box sx={{ maxWidth: 1100, mx: 'auto', minWidth: 0 }}>
      <Button startIcon={<ArrowBack />} onClick={() => navigate('/candidatures')} sx={{ mb: 2 }}>Candidatures</Button>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" spacing={2} sx={{ mb: 3 }}>
        <Box sx={{ minWidth: 0 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <Typography component="h1" variant="h4" sx={{ fontSize: '1.75rem', overflowWrap: 'anywhere' }}>{candidature.titre}</Typography>
            {candidature.archive && <Chip size="small" label="Archivee" variant="outlined" />}
          </Stack>
          <Typography color="text.secondary">{candidature.entreprise || 'Entreprise non renseignee'}</Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
            <Chip size="small" label={TYPES_POSTE[candidature.type_poste] || 'Autre'} variant="outlined" />
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel id="detail-statut-label">Statut</InputLabel>
              <Select labelId="detail-statut-label" label="Statut" value={candidature.statut} disabled={busy}
                onChange={event => patchCandidature({ statut: event.target.value })}>
                {Object.entries(STATUTS).map(([value, option]) => <MenuItem key={value} value={value}>{option.label}</MenuItem>)}
              </Select>
            </FormControl>
            <Tooltip title={candidature.favori ? 'Retirer des favoris' : 'Ajouter aux favoris'}>
              <span><IconButton disabled={busy} color={candidature.favori ? 'warning' : 'default'}
                aria-label={candidature.favori ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                onClick={() => patchCandidature({ favori: !candidature.favori })}>
                {candidature.favori ? <Star /> : <StarBorder />}
              </IconButton></span>
            </Tooltip>
          </Stack>
        </Box>
        <Stack direction="row" useFlexGap flexWrap="wrap" alignContent="flex-start" spacing={1}>
          <Button component={Link} href={candidature.url} target="_blank" rel="noopener noreferrer" startIcon={<OpenInNew />}>Voir l'annonce</Button>
          <Button startIcon={<EditOutlined />} onClick={() => setEditorOpen(true)} disabled={busy}>Modifier</Button>
          <Button startIcon={<ArchiveOutlined />} onClick={() => setConfirmation('archive')} disabled={busy || candidature.archive}>Archiver</Button>
          <Button color="error" startIcon={<DeleteOutline />} onClick={() => setConfirmation('delete')} disabled={busy}>Supprimer</Button>
        </Stack>
      </Stack>

      <Divider />
      <Box component="section" sx={{ py: 3 }}>
        <Typography component="h2" variant="h6" sx={{ mb: 2 }}>Informations generales</Typography>
        <Grid container spacing={2.5}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Entreprise">{candidature.entreprise}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Lieu">{candidature.lieu}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Mode de travail">{MODES_TRAVAIL[candidature.mode_travail]}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Source du canal">{SOURCES_CANAL[candidature.source_canal]}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="CV utilise">{candidature.cv_utilise}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Source extraction">{candidature.source_extraction}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date limite">{dateLabel(candidature.date_limite)}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date de relance">{dateLabel(candidature.date_relance)}</Info></Grid>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}><Info label="Date d'ajout">{dateLabel(candidature.date_ajout, true)}</Info></Grid>
        </Grid>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'flex-start' }} sx={{ mt: 3 }}>
          <Autocomplete multiple freeSolo fullWidth options={[]} value={tags} inputValue={tagInput}
            onChange={(_, value) => setTags(value)} onInputChange={(_, value) => setTagInput(value)} disabled={busy}
            renderInput={params => <TextField {...params} size="small" label="Tags" />} />
          <Button variant="outlined" startIcon={<Save />} disabled={busy || JSON.stringify(tags) === JSON.stringify(candidature.tags || [])}
            onClick={() => patchCandidature({ tags: [...new Set(tags.map(tag => tag.trim()).filter(Boolean))] })}
            sx={{ flexShrink: 0 }}>Enregistrer les tags</Button>
        </Stack>
      </Box>

      <Divider />
      <Box component="section" sx={{ py: 3 }}>
        <Typography component="h2" variant="h6">Description</Typography>
        <Typography sx={{ mt: 1, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{candidature.description || 'Aucune description.'}</Typography>
        <Typography component="h2" variant="h6" sx={{ mt: 3 }}>Notes</Typography>
        <Typography sx={{ mt: 1, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{candidature.notes || 'Aucune note.'}</Typography>
      </Box>

      <Divider sx={{ mb: 3 }} />
      <ActionTimeline actions={actions} disabled={busy} onAdd={() => setActionEditor(null)}
        onEdit={setActionEditor} onDelete={deleteAction} />

      <CandidatureForm open={editorOpen} candidature={candidature} onClose={() => setEditorOpen(false)} onSubmit={saveGeneral} />
      <ActionForm open={actionEditor !== undefined} action={actionEditor || null} onClose={() => setActionEditor(undefined)} onSubmit={saveAction} />
      <Dialog open={Boolean(confirmation)} onClose={() => { if (!busy) setConfirmation(''); }}>
        <DialogTitle>{confirmation === 'archive' ? 'Archiver la candidature ?' : 'Supprimer la candidature ?'}</DialogTitle>
        <DialogContent><Typography>{confirmation === 'archive' ? 'Elle ne figurera plus dans la liste active.' : 'Cette suppression est definitive et effacera son historique.'}</Typography></DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmation('')} disabled={busy}>Annuler</Button>
          <Button color={confirmation === 'delete' ? 'error' : 'primary'} variant="contained" onClick={confirm} disabled={busy}>
            {confirmation === 'archive' ? 'Archiver' : 'Supprimer definitivement'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

