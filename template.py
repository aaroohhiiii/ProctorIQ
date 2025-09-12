import os
from pathlib import Path
import logging
logging.basicConfig(level=logging.INFO, format= '[%(asctime)s]:%(message)s:')

from pathlib import Path
import os
import logging

logging.basicConfig(level=logging.INFO)

list_of_files = [
    # Backend structure matching the exact image
    "exam_automator/backend/main.py",
    "exam_automator/backend/api/routes.py", 
    "exam_automator/backend/api/__init__.py",
    "exam_automator/backend/services/grading_service.py",
    "exam_automator/backend/services/analytics_service.py",
    "exam_automator/backend/services/__init__.py",
    "exam_automator/backend/ocr/extractor.py",
    "exam_automator/backend/ocr/__init__.py",
    "exam_automator/backend/llm/evaluator.py",
    "exam_automator/backend/llm/__init__.py",
    "exam_automator/backend/db/vector_store.py",
    "exam_automator/backend/db/__init__.py",
    "exam_automator/backend/config/settings.py",
    "exam_automator/backend/config/__init__.py",
    "exam_automator/backend/tests/test_grading.py",
    "exam_automator/backend/tests/__init__.py",
    "exam_automator/backend/__init__.py",
    "exam_automator/requirements.txt"
]

for filepath in list_of_files:
    filepath = Path(filepath)
    if filepath.parent != Path('.'):
        filepath.parent.mkdir(parents=True, exist_ok=True)
        logging.info(f'Creating directory: {filepath.parent} for file: {filepath.name}')

    if not filepath.exists() or filepath.stat().st_size == 0:
        filepath.touch()
        logging.info(f'Created empty file: {filepath.name}')
    else:
        logging.info(f'{filepath.name} already exists')


for filepath in list_of_files:
    filepath= Path(filepath)
    if filepath.parent != Path()
