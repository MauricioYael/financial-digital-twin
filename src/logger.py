import os
import logging
from datetime import datetime
import uuid

LOG_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "operational_audit.log")

class StructuredLogger:
    def __init__(self, run_id: str = None):
        self.run_id = run_id or f"R{datetime.now().strftime('%m%d%H%M')}"
        self.logger = logging.getLogger("FinancialDigitalTwin")
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
            formatter = logging.Formatter("%(message)s")
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

    def log_event(self, level: str, stage: str, detail: str, status: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        log_line = f"{timestamp} | {level.upper():<5} | run={self.run_id} | {stage:<10} | {detail} | {status}"
        self.logger.info(log_line)
        print(log_line)

def get_logger(run_id: str = None) -> StructuredLogger:
    return StructuredLogger(run_id)