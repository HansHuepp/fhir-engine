import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os 
from pydantic import BaseModel
import  pandas as pd
from logic_check import get_item, check_item_value

# Install FastAPI and uvicorn if not already installed:
# pip install fastapi uvicorn

DATA_FILE = "data.json"
# test directory
TEST_DIR = "test_files/"
TEST_BOOL = "data_test_boolean.json"
TEST_MULTI = "data_test_multi_condition.json"
TEST_NESTED = "data_test_nested.json"

# TEST_DIR + TEST_BOOL

# Read the JSON file
with open(DATA_FILE, 'r') as file:
    questionnaire = json.load(file)

questionaire_pos = 0
pending_required_question = None


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
    global questionaire_pos, pending_required_question

    # Get the current question's linkId
    current_question = str(questionaire_pos)

    # Load the existing answers into a dictionary if the file exists and is not empty
    if os.path.exists(ANSWERS_FILE) and os.path.getsize(ANSWERS_FILE) > 0:
        with open(ANSWERS_FILE, 'r') as f:
            answers_dict = json.load(f)
    else:
        answers_dict = {}

    # Add the new answer to the dictionary
    answers_dict[current_question] = answer.answer

    # Save updated dictionary back to the JSON file
    with open(ANSWERS_FILE, 'w') as f:
        json.dump(answers_dict, f, indent=4)

    # Check if the current question matches the pending required question
    if pending_required_question == current_question:
        # Reset pending_required_question as it has been answered
        pending_required_question = None

    return {"message": "Answer received and stored."}

@app.get("/nextQuestion")
async def get_next_question(current_link_id: str = None):
    """
    Retrieves the next questionnaire item in depth-first order.

    :param current_link_id: The current linkId (optional).
    :return: The next questionnaire item.
    """
    global questionaire_pos, pending_required_question
    current_link_id = str(questionaire_pos)

    # Check if there’s a pending required question that needs answering
    if pending_required_question:
        # Retrieve and return the pending required question
        required_item = linkid_index.get(pending_required_question)
        if required_item:
            return JSONResponse(
                required_item
            )

    while True:
        # Determine the next question in depth-first order
        if current_link_id is None:
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

        # Retrieve the next item
        next_item = linkid_index.get(next_link_id)
        if next_item is None:
            raise HTTPException(status_code=404, detail="Next item not found")

        # Update the global position
        questionaire_pos = next_link_id
        current_link_id = next_link_id

        # If the item is a group, return it directly without condition checks
        if next_item["type"] == "group":
            return JSONResponse(content=next_item)

        # Skip items that do not meet the enableWhen condition if they are not a group
        if next_item.get("enableWhen"):
            subitem = linkid_index.get(current_link_id)
            df = pd.json_normalize(subitem)
            if not df["enableWhen"].empty:
                enable_when = df["enableWhen"].iloc[0]
                
                if enable_when:
                    for elem in enable_when:
                        question = elem["question"]
                        operator = elem["operator"]
                        answer_string = elem["answerString"]

                        # Check enableWhen condition
                        if not check_item_value(item_id=question, operator=operator, answerString=answer_string):
                            continue  # Skip this item if the condition is not met

                    

        # Check if the item is required
        if next_item.get("required", False):
            # Set the pending required question and return it
            pending_required_question = next_link_id
            return JSONResponse(
                next_item
            )

        # Reset pending_required_question and return the next valid item
        pending_required_question = None
        return JSONResponse(content=next_item)


# @app.get("/nextQuestion")
# async def get_next_question(current_link_id: str = None):
#     """
#     Retrieves the next questionnaire item in depth-first order.

#     :param current_link_id: The current linkId (optional).
#     :return: The next questionnaire item.
#     """
#     global questionaire_pos
#     current_link_id = str(questionaire_pos)
    
#     while True:
#         # Determine the next question in depth-first order
#         if current_link_id is None:
#             # Start with the first item if no current linkId
#             next_link_id = depth_first_order[0]
#         else:
#             try:
#                 index = depth_first_order.index(current_link_id)
#                 next_index = index + 1
#                 if next_index >= len(depth_first_order):
#                     return JSONResponse(content={"message": "No more items"})
#                 next_link_id = depth_first_order[next_index]
#             except ValueError:
#                 raise HTTPException(status_code=404, detail="Current linkId not found")

#         # Retrieve the next item
#         next_item = linkid_index.get(next_link_id)
#         if next_item is None:
#             raise HTTPException(status_code=404, detail="Next item not found")

#         # Update the global position
#         questionaire_pos = next_link_id
#         current_link_id = next_link_id

#         # Skip items that are groups or do not meet the enableWhen condition
#         if next_item["type"] != "group" and next_item.get("enableWhen"):
#             subitem = linkid_index.get(current_link_id)
#             df = pd.json_normalize(subitem)
#             if not df["enableWhen"].empty:
#                 enable_when = df["enableWhen"].iloc[0]
                
#                 if enable_when:
#                     first_condition = enable_when[0]
#                     question = first_condition["question"]
#                     operator = first_condition["operator"]
#                     answer_string = first_condition["answerString"]

#                     # Check enableWhen condition
#                     if not check_item_value(item_id=question, operator=operator, answerString=answer_string):
#                         continue  # Skip this item if the condition is not met

#         # Return the next valid item if all conditions are met
#         return JSONResponse(content=next_item)

# To run the app, use the command:
# uvicorn filename:app --reload
