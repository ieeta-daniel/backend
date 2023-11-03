from typing import Dict, Any

from fastapi import FastAPI
from handler import EndpointHandler

app = FastAPI()
handler = EndpointHandler("something")

@app.post("/", status_code=200)
async def root(input_data: Dict[str, Any]):
    return handler(input_data)
