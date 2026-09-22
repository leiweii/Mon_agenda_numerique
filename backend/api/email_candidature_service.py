VARIABLES_TEMPLATE = (
    'entreprise',
    'nom_contact',
    'prenom_contact',
    'civilite',
    'poste',
    'formation',
    'portfolio_url',
    'github_url',
)

SUBJECT_TEMPLATE = 'Candidature spontanee - Alternance {{ poste }}'
SUBJECT_MAX_LENGTH = 255

BODY_TEMPLATE = '''{{ salutation }},

Je me permets de vous contacter dans le cadre de ma recherche d'une alternance en {{ poste }}.

Actuellement en {{ formation }}, je souhaiterais vous proposer ma candidature au sein de {{ entreprise }}.

Vous trouverez mon CV en piece jointe.

Je reste a votre disposition pour tout echange.

Cordialement,

Leiwei SHI

Portfolio : {{ portfolio_url }}
GitHub : {{ github_url }}'''


def remplacer_variables(template, variables):
    contenu = template
    for variable in VARIABLES_TEMPLATE:
        contenu = contenu.replace(f'{{{{ {variable} }}}}', str(variables.get(variable, '')))
    return contenu


def _construire_salutation(civilite, prenom_contact, nom_contact):
    civilite = civilite.strip()
    nom_contact = nom_contact.strip()
    if not civilite or not nom_contact:
        return 'Bonjour Madame, Monsieur'

    nom_complet = ' '.join(part for part in (prenom_contact.strip(), nom_contact) if part)
    return f'Bonjour {civilite} {nom_complet}'


def preparer_contenu_email(
    *,
    entreprise,
    nom_contact,
    prenom_contact,
    civilite,
    poste,
    formation,
    portfolio_url,
    github_url,
):
    variables = {
        'entreprise': entreprise,
        'nom_contact': nom_contact,
        'prenom_contact': prenom_contact,
        'civilite': civilite,
        'poste': poste,
        'formation': formation,
        'portfolio_url': portfolio_url,
        'github_url': github_url,
    }
    salutation = _construire_salutation(civilite, prenom_contact, nom_contact)
    body = BODY_TEMPLATE.replace('{{ salutation }}', salutation)
    subject = remplacer_variables(SUBJECT_TEMPLATE, variables)
    return {
        'subject': subject[:SUBJECT_MAX_LENGTH],
        'body': remplacer_variables(body, variables),
    }
