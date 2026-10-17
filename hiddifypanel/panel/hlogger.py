import sys
from loguru import logger


def logger_dynamic_formatter(record) -> str:
    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    if record["extra"]:
        fmt += " | <level>{extra}</level>"
    if record["exception"]:
        fmt += "{exception}\n"
    return fmt + "\n"


def init_app(app):
    init_logger(app, False)


def init_cli(app):
    init_logger(app, True)


def init_logger(app, cli):
    # configure logger

    logger.remove()
    logger.add(sys.stderr if cli else sys.stdout, format=logger_dynamic_formatter, level=app.config["STDOUT_LOG_LEVEL"], colorize=True, catch=True, enqueue=True, diagnose=True, backtrace=True)
    logger.trace("Logger initiated :)")

    with app.app_context():
        from hiddifypanel.models.config import hconfig, ConfigEnum

        set_level(app, hconfig(ConfigEnum.log_level))


def set_level(app, level):
    path = app.config["HIDDIFY_CONFIG_PATH"] + "/data/log/panel.log"
    try:
        logger.add(path, format=logger_dynamic_formatter, level=level, colorize=True, catch=True, enqueue=True, diagnose=False, backtrace=True)
    except OSError as e:  # the log file must never stop the panel (e.g. not writable by the panel's user): stderr only
        logger.warning(f"Panel log file {path} not writable ({e}); logging to stderr only")
