import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config

def setup_logging(app):
    if not app.debug:
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(Config.LOG_FILE_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Setup file handler
        file_handler = RotatingFileHandler(
            Config.LOG_FILE_PATH, 
            maxBytes=10240000, 
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(getattr(logging, Config.LOG_LEVEL))
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(getattr(logging, Config.LOG_LEVEL))
        app.logger.info('Parking API startup')