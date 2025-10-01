# Celery integration temporarily disabled
# Uncomment the lines below when Celery is installed and configured

# try:
#     from .celery import app as celery_app
#     __all__ = ('celery_app',)
# except ImportError:
#     print("Warning: Celery not installed. Automated leave management will not work.")
#     __all__ = ()

__all__ = ()