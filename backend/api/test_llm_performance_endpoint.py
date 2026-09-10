from unittest.mock import ANY, patch

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from agenda.models import StatistiqueUtilisation, Tache
from api.models import JournalAppelLLM


class RecommandationIAPerformanceEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='alice', password='secret-password')
        self.task = Tache.objects.create(
            utilisateur=self.user,
            titre='Tache Alice',
            date_echeance=timezone.now(),
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.url = '/api/taches/recommandation_ia/'
        self.recommendation = {
            'heures_recommandees': [10, 15],
            'message': 'Concentrez-vous le matin.',
        }

    def test_cache_hit_returns_cached_recommendation_without_an_llm_call(self):
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=self.recommendation
        ), patch('api.views.journaliser_appel_llm') as journaliser, patch(
            'api.views.appeler_llm'
        ) as appeler_llm, patch('api.views.reserver_appel_llm') as reserver:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.recommendation)
        appeler_llm.assert_not_called()
        reserver.assert_not_called()
        journaliser.assert_called_once_with(
            self.user,
            'prompt nettoye',
            status=JournalAppelLLM.Status.CACHE_HIT,
            cache_hit=True,
        )

    def test_quota_exceeded_returns_latest_cache_without_an_llm_call(self):
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=None), patch(
            'api.views.obtenir_derniere_cache_valide', return_value=self.recommendation
        ), patch('api.views.journaliser_appel_llm') as journaliser, patch(
            'api.views.appeler_llm'
        ) as appeler_llm:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.recommendation)
        appeler_llm.assert_not_called()
        journaliser.assert_called_once_with(
            self.user,
            'prompt nettoye',
            status=JournalAppelLLM.Status.QUOTA_CACHE,
            cache_hit=True,
        )

    def test_quota_exceeded_without_cache_returns_rules_fallback_without_an_llm_call(self):
        StatistiqueUtilisation.objects.create(
            utilisateur=self.user,
            tache=self.task,
            heure_completion='14:00',
            duree_estimee=30,
        )
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=None), patch(
            'api.views.obtenir_derniere_cache_valide', return_value=None
        ), patch('api.views.journaliser_appel_llm') as journaliser, patch(
            'api.views.appeler_llm'
        ) as appeler_llm:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [14],
            'message': 'Vous êtes plus productif vers 14h',
        })
        appeler_llm.assert_not_called()
        journaliser.assert_called_once_with(
            self.user,
            'prompt nettoye',
            status=JournalAppelLLM.Status.QUOTA_FALLBACK,
            cache_hit=False,
        )

    def test_valid_llm_response_is_cached_and_finalizes_the_reservation_as_success(self):
        reservation = object()
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=reservation), patch(
            'api.views.appeler_llm', return_value='{"heures_recommandees": [10, 15], "message": "..."}'
        ), patch('api.views.parser_reponse', return_value=self.recommendation), patch(
            'api.views.ecrire_cache'
        ) as ecrire_cache, patch('api.views.finaliser_appel_llm') as finaliser, patch(
            'api.views.time.monotonic', side_effect=[100.0, 100.125]
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.recommendation)
        ecrire_cache.assert_called_once_with(
            self.user,
            'llm_reco:1:cache',
            self.recommendation,
        )
        finaliser.assert_called_once_with(
            reservation,
            success=True,
            duration_ms=125,
        )

    def test_cache_write_failure_keeps_valid_llm_response_and_finalizes_success(self):
        reservation = object()
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=reservation), patch(
            'api.views.appeler_llm', return_value='{"heures_recommandees": [10, 15], "message": "..."}'
        ), patch('api.views.parser_reponse', return_value=self.recommendation), patch(
            'api.views.ecrire_cache', side_effect=RuntimeError('cache detail confidentiel')
        ), patch('api.views.finaliser_appel_llm') as finaliser, patch(
            'api.views.time.monotonic', side_effect=[100.0, 100.125]
        ), self.assertLogs('api.views', level='WARNING') as logs:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, self.recommendation)
        finaliser.assert_called_once_with(
            reservation,
            success=True,
            duration_ms=125,
        )
        self.assertNotIn('cache detail confidentiel', logs.output[0])

    def test_invalid_llm_response_finalizes_error_and_returns_rules_fallback(self):
        reservation = object()
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=reservation), patch(
            'api.views.appeler_llm', return_value='not-json'
        ), patch('api.views.parser_reponse', return_value=None), patch(
            'api.views.ecrire_cache'
        ) as ecrire_cache, patch('api.views.finaliser_appel_llm') as finaliser, patch(
            'api.views.time.monotonic', side_effect=[100.0, 100.25]
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [],
            'message': 'Pas assez de données pour une recommandation',
        })
        ecrire_cache.assert_not_called()
        finaliser.assert_called_once_with(
            reservation,
            success=False,
            duration_ms=250,
            error_type='InvalidResponse',
        )

    def test_llm_exception_finalizes_error_with_its_type_and_returns_rules_fallback(self):
        reservation = object()
        with patch('api.views.purger_journaux_si_necessaire'), patch(
            'api.views.construire_prompt', return_value='prompt nettoye'
        ), patch('api.views.construire_cle_cache', return_value='llm_reco:1:cache'), patch(
            'api.views.obtenir_cache', return_value=None
        ), patch('api.views.reserver_appel_llm', return_value=reservation), patch(
            'api.views.appeler_llm', side_effect=RuntimeError('detail confidentiel')
        ), patch('api.views.finaliser_appel_llm') as finaliser, patch(
            'api.views.time.monotonic', side_effect=[100.0, 100.25]
        ), self.assertLogs('api.views', level='WARNING') as logs:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'heures_recommandees': [],
            'message': 'Pas assez de données pour une recommandation',
        })
        finaliser.assert_called_once_with(
            reservation,
            success=False,
            duration_ms=250,
            error_type='RuntimeError',
        )
        self.assertNotIn('detail confidentiel', logs.output[0])
