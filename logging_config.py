import logging
import sys
import os

def setup_logging(level=logging.INFO):
    """Configures global logging for Stargwent."""
    
    # Check for debug environment variable
    if os.environ.get('STARGWENT_DEBUG', '').lower() in ('1', 'true', 'yes'):
        level = logging.DEBUG

    # Formatter with colors if in a terminal
    log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    date_format = '%H:%M:%S'

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Set external loggers to WARNING to reduce noise
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    return logging.getLogger('stargwent')
