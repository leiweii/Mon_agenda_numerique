from django.db import migrations, models


def normalize_automatic_theme(apps, schema_editor):
    PreferenceUtilisateur = apps.get_model('agenda', 'PreferenceUtilisateur')
    PreferenceUtilisateur.objects.filter(theme='auto').update(theme='clair')


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0002_alter_tache_couleur'),
    ]

    operations = [
        migrations.RunPython(normalize_automatic_theme, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='preferenceutilisateur',
            name='theme',
            field=models.CharField(
                choices=[('clair', 'Clair'), ('sombre', 'Sombre')],
                default='clair',
                max_length=20,
            ),
        ),
    ]
