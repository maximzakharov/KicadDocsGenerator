import logging
import re
from datetime import datetime
from pathlib import Path


class AnsiColorStripperFormatter(logging.Formatter):
    """
    Custom formatter to remove ANSI color codes from log messages.
    """

    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    def format(self, record):
        formatted_message = super().format(record)

        # Remove ANSI color codes
        cleaned_message = self.ansi_escape.sub("", formatted_message)

        return cleaned_message


def setup_logging(log_level=logging.INFO):
    log_dir = Path.home() / ".KicadDocsGenerator" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = (
        log_dir
        / f"{'KicadDocsGenerator'.lower()}_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    logger.handlers.clear()

    file_formatter = AnsiColorStripperFormatter(
        "%(asctime)s - %(levelname)s: [%(filename)s:%(lineno)d] %(message)s"
    )

    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    logger.addHandler(file_handler)
