import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Read the JSON file
with open('answer.json', 'r') as file:
    answers = json.load(file)

app = FastAPI(title="FHIR Questionnaire Answers API")


@app.get("item/{item_id}")
async def get_item(link_id: str) -> str:
    return answers("item_id")

def get_item(linkid: str, operator: str, answerString: str):
    """
    check if the given item satisfies the condition, e.g. = "Ja"
    """
    answer = answers[linkid]
     # Convert answer and value to boolean if they are "True" or "False", otherwise treat as strings
    if answer in ["True", "False"]:
        parsed_answer = answer == "True"
    else:
        parsed_answer = answer  # Keep as string

    if answerString in ["True", "False"]:
        parsed_value = answerString == "True"
    else:
        parsed_value = answerString  # Keep as string

    # Perform comparison based on the operator
    if operator == "=":
        return parsed_answer == parsed_value
    elif operator == "!=":
        return parsed_answer != parsed_value
    else:
        raise ValueError("Invalid operator for non-numeric data; use '=' or '!=' only")