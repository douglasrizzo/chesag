import logging
import logging.handlers
from pathlib import Path

# create a logger that logs to the console and a file
logger = logging.getLogger(__name__)
logging_level = logging.INFO
logger.setLevel(logging_level)

# create a console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging_level)

# create a file handler with current date as part of the filename and set level to debug
log_file = Path("logs", "games.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
# max 100 files, each 10MB
fh = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=100)
fh.setLevel(logging_level)

# create formatter and add it to the handlers
formatter = logging.Formatter("%(asctime)s|%(levelname)s: %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(ch)
logger.addHandler(fh)


def get_logger():
  return logger
