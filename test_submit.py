import sys
import os
import json
sys.path.append(os.path.abspath('Src'))
from filler import FormFiller

config_path = "WebApp/backend/web_config.json"
filler = FormFiller(config_file=config_path, headless=True, random_mode=False)
filler.fill(num_submissions=1, max_workers=1)
