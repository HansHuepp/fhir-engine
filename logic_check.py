import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI(title="FHIR Questionnaire API")

@app.get("item/{item_id}")
async def get_item(link_id: str) -> dict:


@app.post("istem/{item_id}")



@app.get("item/{item_id}/check")
async def get_item(operator: str, answerString: str):
    """
    check if the given item satisfies the condition, e.g. = "Ja"
    """