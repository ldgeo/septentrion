"""
This is the code around settings loading. For a definition of
the settings, see cli.py (for now)
"""
import logging

logger = logging.getLogger(__name__)


def get_config_settings():
    """
    TODO: read configuration file and return
    a dict with values to use if they are
    not overriden in env vars or CLI flags
    """
    return {}


class Settings(object):
    @staticmethod
    def _clean_key(key):
        return key.upper().replace("-", "_")

    def set(self, **kwargs):
        """
        TODO: clean this.
        """
        kwargs = {self._clean_key(key): value for key, value in kwargs.items()}

        vars(self).update(kwargs)


def log_level(verbosity):
    """
    verbosity  | log level
    (input)    | (output)
    -----------|-------------
    0 ("")     | 40 (ERROR)
    1 ("-v")   | 30 (WARNING)
    2 ("-vv")  | 20 (INFO)
    3 ("-vvv") | 10 (DEBUG)
    """
    return 40 - 10 * min(verbosity, 3)


def consolidate(**kwargs):
    settings.set(**kwargs)

    level = log_level(settings.VERBOSE)
    logging.basicConfig(level=level)
    logger.info("Verbosity level: %s", logging.getLevelName(level))


settings = Settings()
