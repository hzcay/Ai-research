from functools import lru_cache

from src.infrastructure.config.settings import get_settings
from src.utils.logger import setup_logger


@lru_cache()
def init_app_dependencies() -> None:
    settings = get_settings()
    setup_logger(settings.log_level)


def get_settings_dep():
    return get_settings()