import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os 
from pydantic import BaseModel
import  pandas as pd

# Install FastAPI and uvicorn if not already installed:
# pip install fastapi uvicorn

# Read the JSON file
with open('data.json', 'r') as file:
    questionnaire = json.load(file)

questionaire_pos = 0

ANSWERS_FILE = 'answers.json'


app = FastAPI(title="FHIR Questionnaire API")

def build_linkid_index(items, index=None):
    """
    Recursively builds an index of items by their linkId.

    :param items: list of questionnaire items.
    :param index: dictionary to store the items.
    :return: dictionary mapping linkId to items.
    """
    if index is None:
        index = {}
    for item in items:
        link_id = item['linkId']
        index[link_id] = item
        if 'item' in item:
            build_linkid_index(item['item'], index)
    return index

def depth_first_linkIds(items, result=None):
    """
    Recursively builds a list of linkIds in depth-first order.

    :param items: list of questionnaire items.
    :param result: list to store the linkIds.
    :return: list of linkIds in depth-first order.
    """
    if result is None:
        result = []
    for item in items:
        result.append(item['linkId'])
        if 'item' in item:
            depth_first_linkIds(item['item'], result)
    return result

# Build the index
linkid_index = build_linkid_index(questionnaire.get('item', []))

# Build the depth-first order list of linkIds
depth_first_order = depth_first_linkIds(questionnaire.get('item', []))

@app.get("/item/{link_id}")
async def get_item(link_id: str):
    """
    Retrieves a questionnaire item by its linkId.

    :param link_id: The linkId of the item to retrieve.
    :return: The questionnaire item.
    """
    item = linkid_index.get(link_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(content=item)

if not os.path.exists(ANSWERS_FILE):
    pd.DataFrame(columns=["question", "answer"]).to_json(ANSWERS_FILE, orient="records", indent=4)


class Answer(BaseModel):
    answer: str

@app.post("/submit-answer")
async def submit_answer(answer: Answer):
    global questionaire_pos

    # Get the current question's linkId and text
    current_question = str(questionaire_pos)

    # Load the current answers into a DataFrame
    if os.path.exists(ANSWERS_FILE) and os.path.getsize(ANSWERS_FILE) > 0:
        answers_df = pd.read_json(ANSWERS_FILE)
    else:
        answers_df = pd.DataFrame(columns=["question", "answer"])

    # Create a DataFrame row with the current question and received answer
    new_answer_df = pd.DataFrame([{"question": current_question, "answer": answer.answer}])
    print (new_answer_df)
    answers_df = pd.concat([answers_df, new_answer_df], ignore_index=True)

    # Save updated DataFrame back to the JSON file
    answers_df.to_json(ANSWERS_FILE, orient="records", indent=4)

    return {"message": "Answer received and stored."}


@app.get("/nextQuestion")
async def get_next_question(current_link_id: str = None):
    """
    Retrieves the next questionnaire item in depth-first order.

    :param current_link_id: The current linkId (optional).
    :return: The next questionnaire item.
    """
    global questionaire_pos
    current_link_id = str(questionaire_pos)
    
    if current_link_id is None:
        # Return the first item
        next_link_id = depth_first_order[0]
    else:
        try:
            index = depth_first_order.index(current_link_id)
            next_index = index + 1
            if next_index >= len(depth_first_order):
                return JSONResponse(content={"message": "No more items"})
            next_link_id = depth_first_order[next_index]
        except ValueError:
            raise HTTPException(status_code=404, detail="Current linkId not found")

    next_item = linkid_index.get(next_link_id)
    if next_item is None:
        raise HTTPException(status_code=404, detail="Next item not found")
    questionaire_pos = next_link_id
    return JSONResponse(content=next_item)

# To run the app, use the command:
# uvicorn filename:app --reload
