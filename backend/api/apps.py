from django.apps import AppConfig


class ApiConfig(AppConfig):
    default = True
    name = 'api'

    def ready(self):
        import api.signals  # noqa: F401
