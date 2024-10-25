import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Read the JSON file
with open('answer.json', 'r') as file:
    answers = json.load(file)

app = FastAPI(title="FHIR Questionnaire Answers API")


@app.get("item/{item_id}")
async def get_item(link_id: str) -> str:
    answers.question("item_id")

@app.get("item/{item_id}/check")
async def get_item(operator: str, answerString: str):
    """
    check if the given item satisfies the condition, e.g. = "Ja"
    """