"""Extraction legere d'une offre, sans sauvegarde ni appel LLM."""

import http.client
import ipaddress
import socket
import ssl
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TIMEOUT = 6
MAX_BYTES = 1024 * 1024


def normaliser_url(url):
    parts = urlsplit(url.strip())
    host = (parts.hostname or '').lower()
    if ':' in host:
        host = f'[{host}]'
    port = parts.port
    if port and (parts.scheme.lower(), port) not in [('http', 80), ('https', 443)]:
        host += f':{port}'
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if not key.lower().startswith('utm_') and key.lower() not in {'fbclid', 'gclid', 'msclkid'}]
    return urlunsplit((parts.scheme.lower(), host, parts.path or '/', urlencode(query), ''))


def formulaire_vide():
    return {'titre': '', 'entreprise': '', 'description': '',
            'type_poste': 'autre', 'source_extraction': ''}


def telecharger_html(url):
    parts = urlsplit(url)
    if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
        raise ValueError('URL HTTP(S) publique requise')
    port = parts.port or (443 if parts.scheme == 'https' else 80)
    addresses = socket.getaddrinfo(parts.hostname, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise ValueError('Adresse non publique')
    connection = http.client.HTTPConnection(parts.hostname, port, timeout=TIMEOUT)
    try:
        # Connect to the validated IP directly to avoid a second DNS lookup.
        connection.sock = socket.create_connection((addresses[0][4][0], port), timeout=TIMEOUT)
        if parts.scheme == 'https':
            connection.sock = ssl.create_default_context().wrap_socket(connection.sock, server_hostname=parts.hostname)
        target = urlunsplit(('', '', parts.path or '/', parts.query, ''))
        connection.request('GET', target, headers={'User-Agent': 'MonAgenda-Candidatures/1.0', 'Accept': 'text/html', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        # Redirects are not followed: their destination has not been validated.
        if response.status != 200:
            raise ValueError('Statut HTTP non exploitable')
        content_type = response.getheader('Content-Type', '').split(';')[0].strip().lower()
        if content_type not in {'text/html', 'application/xhtml+xml'}:
            raise ValueError('Contenu non HTML')
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError('Reponse trop volumineuse')
        return content.decode(response.headers.get_content_charset() or 'utf-8', errors='replace')
    finally:
        connection.close()


def _nettoyer(text):
    return ' '.join(text.split())


def _description_valide(text):
    return len(text) >= 40 and not any(marker in text.lower() for marker in (
        'cookies', 'cookie policy', 'consent preferences', 'politique de confidentialite',
    ))


class _OffreParser(HTMLParser):
    BLOCKS = {'p', 'div', 'section', 'article', 'main', 'li', 'h1', 'h2', 'br', 'body'}
    IGNORED = {'script', 'style', 'noscript', 'nav', 'footer', 'header'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title = []
        self.in_title = False
        self.ignored = []
        self.current = []
        self.blocks = []

    def flush(self):
        text = _nettoyer(' '.join(self.current))
        if text:
            self.blocks.append(text)
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED:
            self.ignored.append(tag)
        if self.ignored:
            return
        if tag == 'meta':
            attrs = dict(attrs)
            self.meta.setdefault((attrs.get('property') or '').lower(), attrs.get('content') or '')
        if tag == 'title':
            self.in_title = True
        if tag in self.BLOCKS:
            self.flush()

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return
        if tag == 'title':
            self.in_title = False
        if tag in self.BLOCKS:
            self.flush()

    def handle_data(self, data):
        if self.ignored:
            return
        if self.in_title:
            self.title.append(data)
        else:
            self.current.append(data)


def extraire_html(html):
    parser = _OffreParser()
    parser.feed(html)
    parser.close()
    parser.flush()
    titre = _nettoyer(parser.meta.get('og:title', '')) or _nettoyer(' '.join(parser.title))
    description = _nettoyer(parser.meta.get('og:description', ''))
    if not _description_valide(description):
        description = next((text for text in parser.blocks if _description_valide(text)), '')
    if len(titre) < 3 or not description:
        return None
    return {**formulaire_vide(), 'titre': titre[:255], 'description': description, 'source_extraction': 'scraping'}


def scraper_candidature(url, *, contexte=None):
    try:
        html = telecharger_html(url)
        if contexte is not None:
            contexte['html'] = html
        return extraire_html(html)
    except (OSError, ValueError, http.client.HTTPException, LookupError):
        return None
