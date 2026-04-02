import sys
import os
import json
import threading

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional

# Add Src to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../Src')))
from filler import FormFiller
from web_parser import WebFormParser

app = FastAPI(title="AutoFormBot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ParseRequest(BaseModel):
    url: str
    headless: bool = True

class RunRequest(BaseModel):
    config: Dict[str, Any]
    submissions: int = 1
    workers: int = 1
    headless: bool = True
    random_mode: bool = False

@app.post("/api/parse")
def parse_form(req: ParseRequest):
    try:
        parser = WebFormParser(req.url, headless=req.headless)
        result = parser.parse()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_filler_task(config_data: dict, submissions: int, workers: int, headless: bool, random: bool):
    config_path = os.path.join(os.path.dirname(__file__), "web_config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=4)
        
    try:
        filler = FormFiller(config_file=config_path, headless=headless, random_mode=random)
        filler.fill(num_submissions=submissions, max_workers=workers)
    except Exception as e:
        print(f"Error running filler task: {e}")

@app.post("/api/run")
def run_bot(req: RunRequest, background_tasks: BackgroundTasks):
    try:
        # Run filler in a background task so the API doesn't block
        background_tasks.add_task(
            run_filler_task, 
            req.config, 
            req.submissions, 
            req.workers, 
            req.headless, 
            req.random_mode
        )
        return {"status": "success", "message": f"Bot started with {req.submissions} submissions across {req.workers} workers."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
