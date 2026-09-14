import React from 'react';
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd';
import { Box, ButtonBase, Chip, IconButton, Paper, Stack, Tooltip, Typography } from '@mui/material';
import { DragIndicator, Star } from '@mui/icons-material';
import { STATUTS, TYPES_POSTE } from './options';

export default function CandidatureKanban({ candidatures, onStatusChange, onOpen, disabled = false }) {
  const handleDragEnd = result => {
    const { destination, draggableId, source } = result;
    if (!destination || destination.droppableId === source.droppableId || !STATUTS[destination.droppableId]) return;
    const candidature = candidatures.find(item => String(item.id) === draggableId);
    if (candidature) onStatusChange(candidature, destination.droppableId);
  };

  return (
    <DragDropContext onDragEnd={handleDragEnd}>
      <Box sx={{ overflowX: 'auto', pb: 1 }}>
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(220px, 1fr))', gap: 1.5, minWidth: 1120 }}>
          {Object.entries(STATUTS).map(([statut, { label }]) => {
            const items = candidatures.filter(item => item.statut === statut);
            return (
              <Droppable droppableId={statut} key={statut}>
                {(provided, snapshot) => (
                  <Box component="section" ref={provided.innerRef} {...provided.droppableProps}
                    sx={{ minWidth: 0, minHeight: 220, p: 1.25, bgcolor: snapshot.isDraggingOver ? 'action.hover' : 'action.selected', borderTop: 3, borderColor: 'divider' }}>
                    <Typography component="h2" variant="subtitle2" sx={{ mb: 1.25 }}>
                      {label} ({items.length})
                    </Typography>
                    <Stack spacing={1}>
                      {items.map((candidature, index) => (
                        <Draggable draggableId={String(candidature.id)} index={index} key={candidature.id} isDragDisabled={disabled}>
                          {(dragProvided, dragSnapshot) => (
                            <Paper component="article" ref={dragProvided.innerRef} {...dragProvided.draggableProps} variant="outlined"
                              sx={{ p: 1.25, borderRadius: 1, boxShadow: dragSnapshot.isDragging ? 3 : 0, bgcolor: 'background.paper' }}>
                              <Stack direction="row" spacing={0.5} alignItems="flex-start">
                                <ButtonBase onClick={() => onOpen(candidature)} disabled={disabled}
                                  sx={{ minWidth: 0, flex: 1, display: 'block', textAlign: 'left', borderRadius: 0.5 }}>
                                  <Typography component="h3" variant="subtitle2" sx={{ overflowWrap: 'anywhere' }}>
                                    {candidature.titre}
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25, overflowWrap: 'anywhere' }}>
                                    {candidature.entreprise || 'Entreprise non precisee'}
                                  </Typography>
                                </ButtonBase>
                                <Tooltip title={`Deplacer ${candidature.titre}`}>
                                  <span>
                                    <IconButton size="small" aria-label={`Deplacer ${candidature.titre}`} disabled={disabled}
                                      {...dragProvided.dragHandleProps} sx={{ mt: -0.5, mr: -0.5 }}>
                                      <DragIndicator fontSize="small" />
                                    </IconButton>
                                  </span>
                                </Tooltip>
                              </Stack>
                              <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mt: 1 }}>
                                <Chip size="small" label={TYPES_POSTE[candidature.type_poste] || 'Autre'} />
                                {candidature.favori && <Star color="warning" fontSize="small" aria-label="Candidature favorite" />}
                              </Stack>
                            </Paper>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </Stack>
                  </Box>
                )}
              </Droppable>
            );
          })}
        </Box>
      </Box>
    </DragDropContext>
  );
}
