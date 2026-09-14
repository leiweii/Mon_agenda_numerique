import socket
from unittest.mock import patch

from django.test import SimpleTestCase

from api.candidature_scraper import extraire_html, normaliser_url, scraper_candidature
from api.serializers import ImportCandidatureSerializer


DESCRIPTION = 'Construire et maintenir les applications Django de notre equipe produit.'


class ImportURLValidationTests(SimpleTestCase):
    def test_out_of_range_port_is_invalid(self):
        for port in [0, 99999]:
            with self.subTest(port=port):
                serializer = ImportCandidatureSerializer(data={'url': f'https://example.com:{port}/job'})
                self.assertFalse(serializer.is_valid())
                self.assertIn('url', serializer.errors)


class ScraperTests(SimpleTestCase):
    def test_open_graph_extraction_and_whitespace(self):
        result = extraire_html(f'<title>Ignore</title><meta property="og:title" content=" Dev   Django "><meta property="og:description" content="{DESCRIPTION}">')
        self.assertEqual(result['titre'], 'Dev Django')
        self.assertEqual(result['description'], DESCRIPTION)
        self.assertEqual(result['source_extraction'], 'scraping')

    def test_body_fallback_ignores_scripts_styles_and_cookie_banner(self):
        result = extraire_html(f'<title>Dev Django</title><body><script>Ignore</script><style>Ignore</style><p>Accepter tous les cookies pour continuer sur notre site web.</p><p>{DESCRIPTION}</p></body>')
        self.assertEqual(result['description'], DESCRIPTION)

    def test_insufficient_content(self):
        for html in [f'<p>{DESCRIPTION}</p>', f'<title>AB</title><p>{DESCRIPTION}</p>', '<title>Dev</title><p>Trop court</p>', '<title>Dev</title><meta property="og:description" content="Accepter tous les cookies pour continuer sur notre site web.">']:
            with self.subTest(html=html):
                self.assertIsNone(extraire_html(html))

    def test_normalization_preserves_job_parameters(self):
        self.assertEqual(normaliser_url('https://EXAMPLE.com:443/jobs?id=12&utm_source=x&fbclid=x#top'), 'https://example.com/jobs?id=12')

    @patch('api.candidature_scraper.telecharger_html')
    def test_network_failure_returns_empty_result(self, download):
        for error in [TimeoutError(), OSError('network')]:
            download.side_effect = error
            self.assertIsNone(scraper_candidature('https://example.com'))

    @patch('api.candidature_scraper.socket.create_connection')
    @patch('api.candidature_scraper.socket.getaddrinfo')
    def test_private_address_is_never_contacted(self, resolve, connect):
        resolve.return_value = [(2, 1, 6, '', ('127.0.0.1', 443))]
        self.assertIsNone(scraper_candidature('https://example.com'))
        connect.assert_not_called()

    @patch('api.candidature_scraper.socket.create_connection')
    @patch('api.candidature_scraper.socket.getaddrinfo')
    def test_local_and_private_network_ranges_are_blocked(self, resolve, connect):
        private_addresses = (
            (socket.AF_INET, '10.0.0.1'),
            (socket.AF_INET, '172.16.0.1'),
            (socket.AF_INET, '172.31.255.254'),
            (socket.AF_INET, '192.168.1.1'),
            (socket.AF_INET6, '::1'),
            (socket.AF_INET6, 'fe80::1'),
            (socket.AF_INET6, 'fc00::1'),
        )

        for family, address in private_addresses:
            with self.subTest(address=address):
                sockaddr = (
                    (address, 443, 0, 0)
                    if family == socket.AF_INET6
                    else (address, 443)
                )
                resolve.return_value = [
                    (family, socket.SOCK_STREAM, socket.IPPROTO_TCP, '', sockaddr)
                ]
                connect.reset_mock()

                self.assertIsNone(scraper_candidature('https://example.com/offre'))
                connect.assert_not_called()

    @patch('api.candidature_scraper.http.client.HTTPConnection')
    @patch('api.candidature_scraper.socket.create_connection')
    @patch('api.candidature_scraper.socket.getaddrinfo')
    def test_http_status_size_and_success(self, resolve, connect, connection):
        resolve.return_value = [(2, 1, 6, '', ('93.184.216.34', 80))]
        response = connection.return_value.getresponse.return_value
        response.headers.get_content_charset.return_value = 'utf-8'
        response.getheader.return_value = 'text/html'
        for code in [301, 403, 404, 500]:
            response.status = code
            self.assertIsNone(scraper_candidature('http://example.com'))
        response.status = 200
        response.getheader.return_value = 'application/pdf'
        self.assertIsNone(scraper_candidature('http://example.com'))
        response.getheader.return_value = 'text/html'
        response.read.return_value = b'x' * (1024 * 1024 + 1)
        self.assertIsNone(scraper_candidature('http://example.com'))
        response.read.return_value = f'<title>Dev Django</title><p>{DESCRIPTION}</p>'.encode()
        self.assertEqual(scraper_candidature('http://example.com')['titre'], 'Dev Django')
        self.assertEqual(connect.call_args.args[0], ('93.184.216.34', 80))

    @patch('api.candidature_scraper.ssl.create_default_context')
    @patch('api.candidature_scraper.http.client.HTTPConnection')
    @patch('api.candidature_scraper.socket.create_connection')
    @patch('api.candidature_scraper.socket.getaddrinfo')
    def test_https_preserves_hostname_for_certificate_verification(self, resolve, connect, connection, context):
        resolve.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        response = connection.return_value.getresponse.return_value
        response.status = 200
        response.getheader.return_value = 'text/html; charset=utf-8'
        response.headers.get_content_charset.return_value = 'utf-8'
        response.read.return_value = f'<title>Dev Django</title><p>{DESCRIPTION}</p>'.encode()
        self.assertEqual(scraper_candidature('https://example.com')['description'], DESCRIPTION)
        context.return_value.wrap_socket.assert_called_once_with(connect.return_value, server_hostname='example.com')
        connection.return_value.close.assert_called_once()
