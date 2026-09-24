import React from 'react';
import { Box, Button, IconButton, Stack, Tooltip, Typography } from '@mui/material';
import { Add, DeleteOutline, EditOutlined, History } from '@mui/icons-material';
import { format, isValid, parseISO } from 'date-fns';
import { TYPES_ACTION } from './options';

function formatDate(value) {
  const parsed = value ? parseISO(value) : null;
  return parsed && isValid(parsed) ? format(parsed, 'dd/MM/yyyy HH:mm') : '';
}

export default function ActionTimeline({ actions, emails = [], onAdd, onEdit, onDelete, disabled = false }) {
  const emailEvents = emails.flatMap(email => {
    if (!email.created_at) return [];
    const events = [{
      key: `email-created-${email.id}`, kind: 'email', date_action: email.created_at,
      label: `Email préparé — ${email.subject}`, recipient_email: email.recipient_email,
    }];
    if (
      ['draft', 'ready'].includes(email.status)
      && Date.parse(email.updated_at) - Date.parse(email.created_at) > 1000
    ) {
      events.push({
        key: `email-updated-${email.id}`, kind: 'email', date_action: email.updated_at,
        label: `Email mis à jour — ${email.subject}`, recipient_email: email.recipient_email,
      });
    }
    return events;
  });
  const ordered = [
    ...actions.map(action => ({ ...action, key: `action-${action.id}`, kind: 'action', original: action })),
    ...emailEvents,
  ].sort((left, right) => Date.parse(right.date_action) - Date.parse(left.date_action));

  return (
    <Box component="section" aria-labelledby="actions-title">
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <History color="action" />
          <Typography id="actions-title" component="h2" variant="h6">Historique des actions et emails</Typography>
        </Stack>
        <Button startIcon={<Add />} variant="outlined" onClick={onAdd} disabled={disabled}>Ajouter une action</Button>
      </Stack>
      {ordered.length === 0 && <Typography color="text.secondary">Aucune action ni aucun email enregistré.</Typography>}
      <Stack spacing={0} sx={{ borderLeft: 2, borderColor: 'divider', ml: 1.5 }}>
        {ordered.map(item => {
          const label = item.kind === 'email' ? item.label : TYPES_ACTION[item.type_action] || item.type_action;
          return (
            <Box key={item.key} sx={{ position: 'relative', pl: 3, py: 1.5 }}>
              <Box sx={{ position: 'absolute', width: 12, height: 12, borderRadius: '50%', bgcolor: item.kind === 'email' ? 'secondary.main' : 'primary.main', left: -7, top: 24 }} />
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={1}>
                <Box sx={{ minWidth: 0 }}>
                  <Typography component="h3" variant="subtitle2">{label}</Typography>
                  <Typography variant="caption" color="text.secondary">{formatDate(item.date_action)}</Typography>
                  {item.kind === 'email' && <Typography sx={{ mt: 0.5, overflowWrap: 'anywhere' }}>{item.recipient_email}</Typography>}
                  {item.commentaire && <Typography sx={{ mt: 0.5, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.commentaire}</Typography>}
                </Box>
                {item.kind === 'action' && <Stack direction="row">
                  <Tooltip title="Modifier"><span><IconButton size="small" disabled={disabled} aria-label={`Modifier ${label}`} onClick={() => onEdit(item.original)}><EditOutlined fontSize="small" /></IconButton></span></Tooltip>
                  <Tooltip title="Supprimer"><span><IconButton size="small" disabled={disabled} aria-label={`Supprimer ${label}`} onClick={() => onDelete(item.original)}><DeleteOutline fontSize="small" /></IconButton></span></Tooltip>
                </Stack>}
              </Stack>
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}
