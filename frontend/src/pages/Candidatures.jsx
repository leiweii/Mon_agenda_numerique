import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Box, Button, CircularProgress, Dialog, DialogActions, DialogContent, DialogTitle, Grid, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import { Add, DeleteOutline, Refresh, Search, ViewKanban, ViewList, WorkOutline } from '@mui/icons-material';
import CandidatureCard from '../components/Candidatures/CandidatureCard';
import CandidatureForm from '../components/Candidatures/CandidatureForm';
import CandidatureFiltres, { DEFAULT_FILTERS } from '../components/Candidatures/CandidatureFiltres';
import CandidatureKanban from '../components/Candidatures/CandidatureKanban';
import { STATUTS } from '../components/Candidatures/options';
import { candidaturesAPI } from '../services/api';
import { extraireMessageErreur } from '../services/errors';

export default function Candidatures() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryString = searchParams.toString();
  const filters = useMemo(() => {
    const params = new URLSearchParams(queryString);
    return {
      ...DEFAULT_FILTERS,
      search: params.get('search') || '',
      statut: params.getAll('statut'),
      type_poste: params.getAll('type_poste'),
      source_canal: params.getAll('source_canal'),
      tags: params.getAll('tags'),
      favori: params.get('favori') === 'true',
      archive: params.get('archive') === 'true',
      date_ajout_min: params.get('date_ajout_min') || '',
      date_ajout_max: params.get('date_ajout_max') || '',
      date_limite: params.get('date_limite') === '7j',
      relance_due: params.get('relance_due') === 'true',
      ordering: params.get('ordering') || DEFAULT_FILTERS.ordering,
    };
  }, [queryString]);
  const [candidatures, setCandidatures] = useState([]);
  const [knownTags, setKnownTags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [url, setUrl] = useState('');
  const [analysing, setAnalysing] = useState(false);
  const [analysisError, setAnalysisError] = useState('');
  const [editor, setEditor] = useState(null);
  const [deletion, setDeletion] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [viewMode, setViewMode] = useState('liste');
  const [movingId, setMovingId] = useState(null);
  const [moveError, setMoveError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const analysisPending = useRef(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const response = await candidaturesAPI.getAll(new URLSearchParams(queryString));
      setCandidatures(response.data);
      setKnownTags(current => [...new Set([...current, ...response.data.flatMap(item => item.tags || [])])].sort());
    } catch (error) {
      setLoadError(extraireMessageErreur(error, 'Impossible de charger les candidatures.'));
    } finally { setLoading(false); }
  }, [queryString]);
  useEffect(() => { load(); }, [load]);

  const changeFilters = next => {
    const params = new URLSearchParams();
    if (next.search.trim()) params.set('search', next.search.trim());
    for (const key of ['statut', 'type_poste', 'source_canal', 'tags']) {
      next[key].forEach(value => params.append(key, value));
    }
    if (next.favori) params.set('favori', 'true');
    if (next.archive) params.set('archive', 'true');
    if (next.date_ajout_min) params.set('date_ajout_min', next.date_ajout_min);
    if (next.date_ajout_max) params.set('date_ajout_max', next.date_ajout_max);
    if (next.date_limite) params.set('date_limite', '7j');
    if (next.relance_due) params.set('relance_due', 'true');
    if (next.ordering !== DEFAULT_FILTERS.ordering) params.set('ordering', next.ordering);
    setSearchParams(params, { replace: true });
  };

  const analyse = async event => {
    event.preventDefault();
    if (analysisPending.current) return;
    analysisPending.current = true;
    setAnalysing(true);
    setAnalysisError('');
    try {
      const { data } = await candidaturesAPI.importUrl(url.trim());
      if (data.duplicate) {
        const existing = await candidaturesAPI.getById(data.candidature_id);
        setEditor({ candidature: existing.data, message: 'Cette candidature existe deja.' });
      } else {
        setEditor({ candidature: { ...data, url: data.url || url.trim() },
          message: data.source_extraction ? '' : "Aucune information extraite pour cette offre." });
      }
    } catch (error) {
      setAnalysisError(error?.response?.data?.url?.[0] || extraireMessageErreur(error, "Impossible d'analyser ce lien."));
    } finally {
      analysisPending.current = false;
      setAnalysing(false);
    }
  };

  const save = async data => {
    const id = editor?.candidature?.id;
    if (id) await candidaturesAPI.update(id, data);
    else await candidaturesAPI.create(data);
    await load();
    setUrl('');
  };

  const remove = async () => {
    if (deleting) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await candidaturesAPI.delete(deletion.id);
      setCandidatures(current => current.filter(item => item.id !== deletion.id));
      setDeletion(null);
    } catch (error) {
      setDeleteError(extraireMessageErreur(error, 'Impossible de supprimer la candidature.'));
    } finally { setDeleting(false); }
  };

  const changeStatus = async (candidature, statut) => {
    if (movingId !== null) return;
    setMovingId(candidature.id);
    setMoveError('');
    try {
      const { data } = await candidaturesAPI.patch(candidature.id, { statut });
      setCandidatures(current => {
        if (filters.statut.length > 0 && !filters.statut.includes(data.statut)) {
          return current.filter(item => item.id !== candidature.id);
        }
        return current.map(item => item.id === candidature.id ? data : item);
      });
    } catch (error) {
      setMoveError(extraireMessageErreur(error, 'Impossible de mettre a jour le statut.'));
    } finally {
      setMovingId(null);
    }
  };

  const exportCsv = async () => {
    if (exporting) return;
    setExporting(true);
    setExportError('');
    try {
      const { data } = await candidaturesAPI.exportCsv(new URLSearchParams(queryString));
      const downloadUrl = URL.createObjectURL(data);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = 'candidatures.csv';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
    } catch (error) {
      setExportError(extraireMessageErreur(error, "Impossible d'exporter les candidatures."));
    } finally {
      setExporting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', minWidth: 0 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 3 }}>
        <WorkOutline color="primary" />
        <Typography component="h1" variant="h4" sx={{ fontSize: '1.75rem' }}>Candidatures</Typography>
      </Stack>
      <Box component="form" onSubmit={analyse} sx={{ pb: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5}>
          <TextField label="Lien de l'offre" type="url" required size="small" fullWidth value={url}
            onChange={event => setUrl(event.target.value)} disabled={analysing}
            slotProps={{ htmlInput: { maxLength: 1000 } }} />
          <Button type="submit" variant="contained" startIcon={analysing ? <CircularProgress size={18} color="inherit" /> : <Search />}
            disabled={analysing || loading || !url.trim()} sx={{ minWidth: 140 }}>{analysing ? 'Analyse...' : 'Analyser'}</Button>
          <Button startIcon={<Add />} disabled={analysing || loading} onClick={() => setEditor({ candidature: null })}
            sx={{ flexShrink: 0 }}>Ajouter manuellement</Button>
        </Stack>
        {analysisError && <Alert severity="error" sx={{ mt: 2 }}>{analysisError}</Alert>}
      </Box>
      <CandidatureFiltres filters={filters} onChange={changeFilters} tagsDisponibles={knownTags}
        onExport={exportCsv} exporting={exporting} />
      {exportError && <Alert severity="error" sx={{ mt: 2 }}>{exportError}</Alert>}
      {loading ? <Box role="status" aria-label="Chargement des candidatures" sx={{ py: 5, textAlign: 'center' }}><CircularProgress /></Box>
        : loadError ? <Alert severity="error" sx={{ mt: 3 }} action={<Button startIcon={<Refresh />} onClick={load}>Reessayer</Button>}>{loadError}</Alert>
          : <>
            <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2} sx={{ my: 3 }}>
              <Typography component="p" variant="body2" color="text.secondary">
                {candidatures.length} candidature{candidatures.length !== 1 ? 's' : ''}
              </Typography>
              <ToggleButtonGroup exclusive size="small" value={viewMode} aria-label="Mode d affichage"
                onChange={(_, value) => { if (value) setViewMode(value); }}>
                <ToggleButton value="liste" aria-label="Vue Liste"><ViewList fontSize="small" /></ToggleButton>
                <ToggleButton value="kanban" aria-label="Vue Kanban"><ViewKanban fontSize="small" /></ToggleButton>
              </ToggleButtonGroup>
            </Stack>
            {moveError && <Alert severity="error" sx={{ mb: 2 }}>{moveError}</Alert>}
            {candidatures.length === 0 && viewMode === 'liste' && <Box sx={{ py: 6, textAlign: 'center' }}>
              <WorkOutline color="disabled" sx={{ fontSize: 40, mb: 1 }} />
              <Typography component="h2" variant="h6" color="text.secondary">Aucune candidature</Typography>
            </Box>}
            {viewMode === 'kanban'
              ? <CandidatureKanban candidatures={candidatures} onStatusChange={changeStatus}
                onOpen={candidature => navigate(`/candidatures/${candidature.id}`)} disabled={movingId !== null} />
              : Object.entries(STATUTS).map(([statut, { label }]) => {
              const items = candidatures.filter(item => item.statut === statut).sort((a, b) => (Date.parse(b.date_ajout) || 0) - (Date.parse(a.date_ajout) || 0));
              return items.length > 0 && <Box component="section" key={statut} sx={{ mb: 4 }}>
                <Typography component="h2" variant="h6" sx={{ mb: 1.5, fontSize: '1rem' }}>{label} ({items.length})</Typography>
                <Grid container spacing={2}>
                  {items.map(item => <Grid key={item.id} size={{ xs: 12, md: 6 }} sx={{ minWidth: 0 }}>
                    <CandidatureCard candidature={item} disabled={analysing} onEdit={candidature => setEditor({ candidature })}
                      onOpen={candidature => navigate(`/candidatures/${candidature.id}`)}
                      onDelete={candidature => { setDeleteError(''); setDeletion(candidature); }} />
                  </Grid>)}
                </Grid>
              </Box>;
            })}
          </>}
      <CandidatureForm open={Boolean(editor)} candidature={editor?.candidature} message={editor?.message}
        onClose={() => setEditor(null)} onSubmit={save} />
      <Dialog open={Boolean(deletion)} onClose={() => { if (!deleting) setDeletion(null); }} aria-labelledby="delete-candidature-title">
        <DialogTitle id="delete-candidature-title">Supprimer la candidature ?</DialogTitle>
        <DialogContent>
          {deleteError && <Alert severity="error" sx={{ mb: 2 }}>{deleteError}</Alert>}
          <Typography sx={{ overflowWrap: 'anywhere' }}>{deletion?.titre}</Typography>
        </DialogContent>
        <DialogActions>
          <Button disabled={deleting} onClick={() => setDeletion(null)}>Annuler</Button>
          <Button disabled={deleting} color="error" startIcon={<DeleteOutline />} onClick={remove}>{deleting ? 'Suppression...' : 'Supprimer'}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
