from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.test import TestCase
from unittest.mock import patch

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .email_candidature_service import VARIABLES_TEMPLATE, preparer_contenu_email, remplacer_variables
from .models import Candidature, CVUtilisateur, EmailCandidature


class EmailCandidatureModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='email-owner')
        self.other_user = User.objects.create_user(username='other-email-owner')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/email-owner',
            titre='Developpeur backend',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/other-email-owner',
            titre='Developpeur frontend',
        )

    def test_new_email_is_a_draft_by_default(self):
        email = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='recrutement@example.com',
            subject='Candidature spontanee',
            body='Bonjour,',
        )

        self.assertEqual(email.status, 'draft')

    def test_email_statuses_cover_the_validated_workflow(self):
        self.assertEqual(
            {value for value, _label in EmailCandidature.Status.choices},
            {'draft', 'ready', 'sending', 'sent', 'failed', 'cancelled'},
        )

    def test_emails_are_scoped_through_the_candidature_owner(self):
        own_email = EmailCandidature.objects.create(
            candidature=self.candidature,
            recipient_email='own@example.com',
            subject='Own application',
            body='Own body',
        )
        EmailCandidature.objects.create(
            candidature=self.other_candidature,
            recipient_email='other@example.com',
            subject='Other application',
            body='Other body',
        )

        visible_ids = set(
            EmailCandidature.objects.filter(
                candidature__utilisateur=self.user,
            ).values_list('id', flat=True)
        )

        self.assertEqual(visible_ids, {own_email.id})


class CVUtilisateurModelTests(TestCase):
    def test_default_cv_is_scoped_to_its_user(self):
        user = User.objects.create_user(username='cv-owner')
        other_user = User.objects.create_user(username='other-cv-owner')
        own_cv = CVUtilisateur.objects.create(
            utilisateur=user,
            fichier='cv/cv-owner.pdf',
        )
        CVUtilisateur.objects.create(
            utilisateur=other_user,
            fichier='cv/other-cv-owner.pdf',
        )

        self.assertEqual(user.cv_par_defaut, own_cv)
        self.assertEqual(user.cv_par_defaut.fichier.name, 'cv/cv-owner.pdf')

    def test_user_cannot_have_two_default_cvs(self):
        user = User.objects.create_user(username='single-cv-owner')
        CVUtilisateur.objects.create(
            utilisateur=user,
            fichier='cv/first.pdf',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CVUtilisateur.objects.create(
                utilisateur=user,
                fichier='cv/second.pdf',
            )


class EmailCandidatureTemplateTests(TestCase):
    def test_replaces_each_supported_variable(self):
        for variable in VARIABLES_TEMPLATE:
            with self.subTest(variable=variable):
                template = f'Avant {{{{ {variable} }}}} apres'

                rendered = remplacer_variables(template, {variable: f'valeur-{variable}'})

                self.assertEqual(rendered, f'Avant valeur-{variable} apres')

    def test_prepared_content_uses_all_template_values(self):
        content = preparer_contenu_email(
            entreprise='Doctolib',
            nom_contact='Martin',
            prenom_contact='Sophie',
            civilite='Madame',
            poste='Developpeur Full Stack',
            formation='Licence Professionnelle Projet Web et Mobile',
            portfolio_url='https://portfolio.example.com',
            github_url='https://github.com/example',
        )

        for expected in (
            'Doctolib',
            'Martin',
            'Sophie',
            'Madame',
            'Developpeur Full Stack',
            'Licence Professionnelle Projet Web et Mobile',
            'https://portfolio.example.com',
            'https://github.com/example',
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, content['subject'] + content['body'])

    def test_uses_generic_salutation_when_contact_or_civility_is_missing(self):
        incomplete_contacts = (
            {'civilite': '', 'prenom_contact': 'Sophie', 'nom_contact': 'Martin'},
            {'civilite': 'Madame', 'prenom_contact': '', 'nom_contact': ''},
        )

        for contact in incomplete_contacts:
            with self.subTest(contact=contact):
                content = preparer_contenu_email(
                    entreprise='Doctolib',
                    poste='Developpeur Full Stack',
                    formation='Licence Professionnelle',
                    portfolio_url='https://portfolio.example.com',
                    github_url='https://github.com/example',
                    **contact,
                )

                self.assertTrue(content['body'].startswith('Bonjour Madame, Monsieur'))


class EmailCandidaturePreparationEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='draft-owner')
        self.other_user = User.objects.create_user(username='draft-other-owner')
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user,
            url='https://example.com/draft-owner',
            titre='Developpeur Full Stack',
            entreprise='Doctolib',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other_user,
            url='https://example.com/draft-other-owner',
            titre='Developpeur Backend',
            entreprise='Entreprise privee',
        )
        self.payload = {
            'recipient_email': 'sophie.martin@example.com',
            'civilite': 'Madame',
            'prenom_contact': 'Sophie',
            'nom_contact': 'Martin',
            'formation': 'Licence Professionnelle Projet Web et Mobile',
            'portfolio_url': 'https://portfolio.example.com',
            'github_url': 'https://github.com/example',
        }

    @patch('socket.create_connection')
    def test_prepares_draft_without_any_gmail_or_network_request(self, connection_mock):
        response = self.client.post(
            f'/api/candidatures/{self.candidature.id}/preparer_email/',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        email = EmailCandidature.objects.get(pk=response.data['id'])
        self.assertEqual(email.candidature, self.candidature)
        self.assertEqual(email.status, EmailCandidature.Status.DRAFT)
        self.assertEqual(email.recipient_email, 'sophie.martin@example.com')
        self.assertIn('Doctolib', email.body)
        self.assertIn('Developpeur Full Stack', email.subject + email.body)
        connection_mock.assert_not_called()

    def test_cannot_prepare_draft_for_another_users_candidature(self):
        response = self.client.post(
            f'/api/candidatures/{self.other_candidature.id}/preparer_email/',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(EmailCandidature.objects.exists())

    def test_prepares_draft_when_candidature_title_uses_model_max_length(self):
        self.candidature.titre = 'P' * 255
        self.candidature.save(update_fields=['titre'])

        response = self.client.post(
            f'/api/candidatures/{self.candidature.id}/preparer_email/',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertLessEqual(len(response.data['subject']), 255)

    def test_rejects_recipient_email_longer_than_model_field(self):
        payload = {
            **self.payload,
            'recipient_email': f"{'a' * 250}@example.com",
        }

        response = self.client.post(
            f'/api/candidatures/{self.candidature.id}/preparer_email/',
            payload,
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmailCandidature.objects.exists())


class EmailCandidatureDraftEndpointTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='email-draft-user')
        self.other_user = User.objects.create_user(username='other-draft-user')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=self.user).key}')
        self.candidature = Candidature.objects.create(
            utilisateur=self.user, url='https://example.com/draft', titre='Developpeur',
        )
        self.other_candidature = Candidature.objects.create(
            utilisateur=self.other_user, url='https://example.com/other-draft', titre='Developpeur',
        )
        self.draft = EmailCandidature.objects.create(
            candidature=self.candidature, recipient_email='first@example.com',
            subject='First subject', body='First body',
        )
        self.other_draft = EmailCandidature.objects.create(
            candidature=self.other_candidature, recipient_email='private@example.com',
            subject='Private subject', body='Private body',
        )

    def test_edits_owned_draft_fields_without_accepting_status_or_parent(self):
        response = self.client.patch(
            f'/api/candidatures/{self.candidature.id}/emails/{self.draft.id}/',
            {
                'recipient_email': 'updated@example.com', 'subject': 'Updated subject',
                'body': 'Updated body', 'status': 'sent',
                'candidature': self.other_candidature.id,
            }, format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.recipient_email, 'updated@example.com')
        self.assertEqual(self.draft.subject, 'Updated subject')
        self.assertEqual(self.draft.body, 'Updated body')
        self.assertEqual(self.draft.status, EmailCandidature.Status.DRAFT)
        self.assertEqual(self.draft.candidature, self.candidature)

    def test_cancels_owned_draft_and_rejects_later_edits(self):
        url = f'/api/candidatures/{self.candidature.id}/emails/{self.draft.id}/'

        response = self.client.post(f'{url}annuler/')

        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, EmailCandidature.Status.CANCELLED)
        self.assertEqual(self.client.patch(url, {'subject': 'Changed'}, format='json').status_code, 400)

    @patch('socket.create_connection')
    def test_prepares_ready_draft_without_gmail_request(self, connection_mock):
        CVUtilisateur.objects.create(utilisateur=self.user, fichier='cv/cv-user.pdf')
        url = f'/api/candidatures/{self.candidature.id}/emails/{self.draft.id}/preparer_envoi/'

        response = self.client.post(url, {
            'recipient_email': 'ready@example.com', 'subject': 'Ready subject',
            'body': 'Ready body',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.draft.refresh_from_db()
        self.assertEqual(self.draft.status, EmailCandidature.Status.READY)
        self.assertEqual(self.draft.recipient_email, 'ready@example.com')
        self.assertIsNone(self.draft.sent_at)
        self.assertEqual(self.draft.gmail_message_id, '')
        connection_mock.assert_not_called()

    def test_other_users_drafts_are_inaccessible_even_under_owned_parent(self):
        urls = (
            f'/api/candidatures/{self.other_candidature.id}/emails/{self.other_draft.id}/',
            f'/api/candidatures/{self.candidature.id}/emails/{self.other_draft.id}/',
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.patch(url, {'subject': 'Stolen'}, format='json').status_code, 404)

    def test_cv_name_is_scoped_to_authenticated_user(self):
        CVUtilisateur.objects.create(utilisateur=self.user, fichier='cv/mine.pdf')
        CVUtilisateur.objects.create(utilisateur=self.other_user, fichier='cv/private.pdf')

        response = self.client.get('/api/candidatures/cv_par_defaut/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['filename'], 'mine.pdf')
