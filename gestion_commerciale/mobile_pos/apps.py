from django.apps import AppConfig


class MobilePosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mobile_pos'

    def ready(self):
        import mobile_pos.signals
