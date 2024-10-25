import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Read the JSON file
with open('answers.json', 'r') as file:
    answers = json.load(file)

app = FastAPI(title="FHIR Questionnaire Answers API")


def get_item(item_id: str) -> str:
    # Read the JSON file
    try: 
        with open('answers.json', 'r') as file:
            answers = json.load(file)
    except Exception:
        raise KeyError

    return answers.get(item_id)

def check_item_value(item_id: str, operator: str, answerString: str):
    """
    check if the given item satisfies the condition, e.g. = "Ja"
    """
    # Read the JSON file
    with open('answers.json', 'r') as file:
        answers = json.load(file)
    answer = answers[item_id]
    
    if operator == "=":
        return answer == answerString
    else:
        raise ValueError("Invalid operator for non-numeric data; use '=' or '!=' only")