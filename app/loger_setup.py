import logging

def get_logger(name: str, level="INFO", console_level=None, file_level=None) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level if level else "INFO")

    if logger.handlers:
        return logger  # Уже настроен

    formatter = logging.Formatter(
        "%(asctime)s — %(name)s — %(levelname)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Файловый лог
    file_handler = logging.FileHandler("app.log", mode="a", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(file_level if file_level else level)
    logger.addHandler(file_handler)

    # Консольный лог
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(console_level if console_level else level)
    logger.addHandler(console_handler)

    return logger
