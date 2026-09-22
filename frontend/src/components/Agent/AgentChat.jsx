import React, { useEffect, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  CircularProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';

import { agentAPI } from '../../services/api';

const CONVERSATION_STORAGE_KEY = 'agentConversationId';

const toolSummaries = {
  get_today_tasks: 'Tâches du jour consultées.',
  get_applications: 'Candidatures consultées.',
};

const readableError = (error, fallback) => (
  error?.response?.data?.erreur
  || error?.response?.data?.detail
  || fallback
);

function MessageBubble({ message }) {
  const isUser = message.role === 'utilisateur';
  const content = message.role === 'outil'
    ? toolSummaries[message.tool_name] || 'Informations consultées.'
    : message.contenu;

  return (
    <Box sx={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <Paper
        elevation={0}
        sx={{
          bgcolor: isUser ? 'primary.main' : 'action.hover',
          color: isUser ? 'primary.contrastText' : 'text.primary',
          maxWidth: { xs: '92%', sm: '75%' },
          px: 2,
          py: 1.5,
          whiteSpace: 'pre-wrap',
        }}
      >
        <Typography variant="body1">{content}</Typography>
      </Paper>
    </Box>
  );
}

function AgentChat() {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [actions, setActions] = useState([]);
  const [input, setInput] = useState('');
  const [generating, setGenerating] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [processingActionId, setProcessingActionId] = useState(null);
  const [error, setError] = useState('');
  const endRef = useRef(null);

  useEffect(() => {
    const storedId = Number(localStorage.getItem(CONVERSATION_STORAGE_KEY));
    if (!Number.isInteger(storedId) || storedId <= 0) {
      setLoadingHistory(false);
      return;
    }

    let active = true;
    agentAPI.getConversation(storedId)
      .then(({ data }) => {
        if (!active) return;
        setConversationId(data.conversation_id);
        setMessages(data.messages || []);
        setActions(data.actions_en_attente || []);
      })
      .catch((requestError) => {
        if (!active) return;
        if (requestError?.response?.status === 404) {
          localStorage.removeItem(CONVERSATION_STORAGE_KEY);
        } else {
          setError(readableError(requestError, 'Impossible de recharger la conversation.'));
        }
      })
      .finally(() => {
        if (active) setLoadingHistory(false);
      });

    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (typeof endRef.current?.scrollIntoView === 'function') {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, actions]);

  const sendMessage = async (event) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || generating) return;

    setError('');
    setInput('');
    setGenerating(true);
    setMessages(current => [...current, {
      id: `local-user-${Date.now()}`,
      role: 'utilisateur',
      contenu: message,
    }]);

    try {
      const payload = conversationId ? { conversation_id: conversationId, message } : { message };
      const { data } = await agentAPI.sendMessage(payload);
      setConversationId(data.conversation_id);
      localStorage.setItem(CONVERSATION_STORAGE_KEY, String(data.conversation_id));
      setMessages(current => [...current, {
        id: `local-agent-${Date.now()}`,
        role: 'agent',
        contenu: data.message,
      }]);
      if (data.action_en_attente) {
        setActions(current => [...current, {
          ...data.action_en_attente,
          statut: 'en_attente',
        }]);
      }
    } catch (requestError) {
      setError(readableError(requestError, "L'assistant n'a pas pu répondre."));
    } finally {
      setGenerating(false);
    }
  };

  const processAction = async (actionId, decision) => {
    setError('');
    setProcessingActionId(actionId);
    try {
      if (decision === 'confirmer') {
        await agentAPI.confirmAction(actionId);
      } else {
        await agentAPI.cancelAction(actionId);
      }
      const status = decision === 'confirmer' ? 'confirmee' : 'annulee';
      const feedback = decision === 'confirmer' ? 'Action confirmée.' : 'Action annulée.';
      setActions(current => current.map(action => (
        action.id === actionId ? { ...action, statut: status } : action
      )));
      setMessages(current => [...current, {
        id: `local-action-${actionId}-${status}`,
        role: 'agent',
        contenu: feedback,
      }]);
    } catch (requestError) {
      setError(readableError(requestError, "L'action n'a pas pu être traitée."));
    } finally {
      setProcessingActionId(null);
    }
  };

  return (
    <Stack spacing={2} sx={{ maxWidth: 960, mx: 'auto' }}>
      <Box>
        <Typography variant="h4" component="h1">Assistant</Typography>
        <Typography color="text.secondary">
          Organisez vos tâches et consultez vos candidatures en conversation.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper
        variant="outlined"
        aria-label="Conversation avec l'assistant"
        sx={{
          minHeight: { xs: '58vh', sm: 560 },
          maxHeight: '70vh',
          overflowY: 'auto',
          p: { xs: 2, sm: 3 },
        }}
      >
        <Stack spacing={2}>
          {loadingHistory && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress aria-label="Chargement de la conversation" />
            </Box>
          )}
          {!loadingHistory && messages.length === 0 && actions.length === 0 && (
            <Typography color="text.secondary" align="center" sx={{ py: 4 }}>
              Décrivez ce que vous souhaitez planifier.
            </Typography>
          )}
          {messages.map(message => <MessageBubble key={message.id} message={message} />)}
          {actions.map(action => (
            <Card key={action.id} variant="outlined" sx={{ borderColor: 'warning.main' }}>
              <CardContent>
                <Typography variant="overline" color="warning.dark">Confirmation requise</Typography>
                <Typography>{action.description}</Typography>
                {action.statut === 'confirmee' && <Typography color="success.main">Confirmée</Typography>}
                {action.statut === 'annulee' && <Typography color="text.secondary">Annulée</Typography>}
              </CardContent>
              {action.statut === 'en_attente' && (
                <CardActions>
                  <Button
                    variant="contained"
                    color="success"
                    disabled={processingActionId !== null}
                    onClick={() => processAction(action.id, 'confirmer')}
                  >
                    Confirmer
                  </Button>
                  <Button
                    variant="outlined"
                    disabled={processingActionId !== null}
                    onClick={() => processAction(action.id, 'annuler')}
                  >
                    Annuler
                  </Button>
                </CardActions>
              )}
            </Card>
          ))}
          {generating && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">L’assistant réfléchit…</Typography>
            </Box>
          )}
          <div ref={endRef} />
        </Stack>
      </Paper>

      <Box component="form" onSubmit={sendMessage} sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          label="Votre message"
          value={input}
          disabled={generating}
          onChange={event => setInput(event.target.value)}
          multiline
          maxRows={4}
        />
        <Button
          type="submit"
          variant="contained"
          endIcon={<SendIcon />}
          disabled={generating || !input.trim()}
          aria-label={generating ? 'Génération en cours' : 'Envoyer'}
        >
          {generating ? 'En cours…' : 'Envoyer'}
        </Button>
      </Box>
    </Stack>
  );
}

export default AgentChat;
