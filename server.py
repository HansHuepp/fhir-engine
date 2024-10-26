import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd

# Assume the logic_check module has been appropriately modified to accept answers_dict
# from logic_check import get_item, check_item_value

# Install FastAPI and uvicorn if not already installed:
# pip install fastapi uvicorn

DATA_FILE = "data.json"
TEST_DIR = "test_files/"
TEST_BOOL = "data_test_boolean.json"
TEST_MULTI = "data_test_multi_condition.json"
TEST_NESTED = "data_test_nested.json"
TEST_NEW = "data_test_NEW.json"

SESSIONS_DIR = 'sessions/'
if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)

# Read the JSON file
with open(TEST_DIR + TEST_NEW, 'r') as file:
    questionnaire = json.load(file)

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

def load_session(session_id):
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}_state.json")
    if os.path.exists(session_file):
        with open(session_file, 'r') as f:
            session_data = json.load(f)
    else:
        # Initialize session data
        session_data = {
            'questionaire_pos': 0,
            'pending_required_question': None,
        }
    return session_data

def save_session(session_id, session_data):
    session_file = os.path.join(SESSIONS_DIR, f"{session_id}_state.json")
    with open(session_file, 'w') as f:
        json.dump(session_data, f)

def load_answers(session_id):
    answers_file = os.path.join(SESSIONS_DIR, f"{session_id}_answers.json")
    if os.path.exists(answers_file):
        with open(answers_file, 'r') as f:
            answers_dict = json.load(f)
    else:
        answers_dict = {}
    return answers_dict

def save_answers(session_id, answers_dict):
    answers_file = os.path.join(SESSIONS_DIR, f"{session_id}_answers.json")
    with open(answers_file, 'w') as f:
        json.dump(answers_dict, f, indent=4)

@app.get("/answeredQuestions/{session_id}")
async def get_answered_questions(session_id: str):
    """
    Retrieves all the questions that have been answered along with the answers.

    :param session_id: The session identifier.
    :return: A list of questions and their corresponding answers.
    """
    # Load the existing answers
    answers_dict = load_answers(session_id)

    if not answers_dict:
        raise HTTPException(status_code=404, detail="No answers found for this session")

    # For each answered linkId, get the question item
    answered_questions = []
    for link_id, answer in answers_dict.items():
        question_item = linkid_index.get(link_id)
        if question_item:
            answered_questions.append({
                'linkId': link_id,
                'text': question_item.get('text'),
                'type': question_item.get('type'),
                'answer': answer
            })
        else:
            # Handle the case where the linkId does not exist in the index
            answered_questions.append({
                'linkId': link_id,
                'text': "Question not found",
                'type': None,
                'answer': answer
            })

    return JSONResponse(content=answered_questions)

def check_item_value(item_id, operator, answerString=None, answerBoolean=None, answers=None):
    """
    Checks if the answer to a specific question meets a condition.

    :param item_id: The linkId of the question to check.
    :param operator: The operator to use for comparison.
    :param answerString: The string value to compare against.
    :param answerBoolean: The boolean value to compare against.
    :param answers: The dictionary of user answers.
    :return: True if the condition is met, False otherwise.
    """
    if answers is None:
        answers = {}
    user_answer = answers.get(item_id)

    if answerString is not None:
        if operator == '=':
            return user_answer == answerString
        elif operator == '!=':
            return user_answer != answerString
        # Add other operators as needed
    elif answerBoolean is not None:
        if operator == '=':
            return user_answer == answerBoolean
        elif operator == '!=':
            return user_answer != answerBoolean
        # Add other operators as needed

    return False

@app.get("/item/{link_id}")
async def get_item_endpoint(link_id: str):
    """
    Retrieves a questionnaire item by its linkId.

    :param link_id: The linkId of the item to retrieve.
    :return: The questionnaire item.
    """
    item = linkid_index.get(link_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(content=item)

class Answer(BaseModel):
    answer: str

@app.post("/submit-answer/{session_id}")
async def submit_answer(session_id: str, answer: Answer):
    # Load session data
    session_data = load_session(session_id)
    questionaire_pos = session_data.get('questionaire_pos', 0)
    pending_required_question = session_data.get('pending_required_question')

    # Get the current question's linkId
    current_question = str(questionaire_pos)

    # Load the existing answers
    answers_dict = load_answers(session_id)

    # Add the new answer to the dictionary
    answers_dict[current_question] = answer.answer

    # Save updated answers back to the JSON file
    save_answers(session_id, answers_dict)

    # Check if the current question matches the pending required question
    if pending_required_question == current_question:
        # Reset pending_required_question as it has been answered
        session_data['pending_required_question'] = None

    # Save session data
    save_session(session_id, session_data)

    return {"message": "Answer received and stored."}

@app.get("/nextQuestion/{session_id}")
async def get_next_question(session_id: str, current_link_id: str = None):
    """
    Retrieves the next questionnaire item in depth-first order.

    :param session_id: The session identifier.
    :param current_link_id: The current linkId (optional).
    :return: The next questionnaire item.
    """
    # Load session data
    session_data = load_session(session_id)
    questionaire_pos = session_data.get('questionaire_pos', 0)
    pending_required_question = session_data.get('pending_required_question')

    current_link_id = str(questionaire_pos)

    # Load the existing answers
    answers_dict = load_answers(session_id)

    # Check if there’s a pending required question that needs answering
    if pending_required_question:
        # Retrieve and return the pending required question
        required_item = linkid_index.get(pending_required_question)
        if required_item:
            return JSONResponse(content=required_item)

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

        # Update the session's position
        session_data['questionaire_pos'] = next_link_id
        current_link_id = next_link_id

        # If the item is a group, return it directly without condition checks
        if next_item["type"] == "group":
            # Save session data
            save_session(session_id, session_data)
            return JSONResponse(content=next_item)

        # Skip items that do not meet the enableWhen condition if they are not a group
        enable_when_temp = False
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

                        # Check enableWhen condition using session-specific answers
                        if not check_item_value(
                                item_id=question,
                                operator=operator,
                                answerString=answer_string,
                                answers=answers_dict):
                            enable_when_temp = True
                            continue  # Skip this item if the condition is not met

        if enable_when_temp:
            continue
        # Check if the item is required
        if next_item.get("required", False):
            # Set the pending required question and return it
            session_data['pending_required_question'] = next_link_id
            # Save session data
            save_session(session_id, session_data)
            return JSONResponse(content=next_item)

        # Reset pending_required_question and return the next valid item
        session_data['pending_required_question'] = None
        # Save session data
        save_session(session_id, session_data)
        return JSONResponse(content=next_item)
