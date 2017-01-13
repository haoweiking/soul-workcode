

from redis import StrictRedis
import collections

__all__ = ('Redis', )


class Redis(object):

    def __init__(self, app=None, config_prefix=None):
        """
        Constructor for non-factory Flask applications
        """

        self.config_prefix = config_prefix or 'redis'

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Apply the Flask app configuration to a Redis object
        """
        self.app = app

        self.key = lambda suffix: '{0}_{1}'.format(
            self.config_prefix,
            suffix
        )

        self.app.settings.setdefault(self.key('url'), 'redis://localhost:6379')

        db = self.app.settings.get(self.key('database'))

        self.connection = connection = StrictRedis.from_url(
            self.app.settings.get(self.key('url')),
            db=db,
            decode_responses=True
        )

        self._include_connection_methods(connection)

    def _include_connection_methods(self, connection):
        """
        Include methods from connection instance to current instance.
        """
        for attr in dir(connection):
            value = getattr(connection, attr)
            if attr.startswith('_') or not isinstance(value, collections.Callable):
                continue

            self.__dict__[attr] = value
