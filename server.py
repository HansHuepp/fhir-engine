import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Load JSON data file
DATA_FILE = "data.json"
TEST_DIR = "test_files/"
TEST_BOOL = "data_test_boolean.json"
TEST_MULTI = "data_test_multi_condition.json"
TEST_NESTED = "data_test_nested.json"
ANSWERS_FILE = 'answers.json'
with open(DATA_FILE, 'r') as file:
    questionnaire = json.load(file)

# Initialize FastAPI
app = FastAPI(title="FHIR Questionnaire API")

# Initialize the traversal state
traversal_stack = []  # Stack for managing preorder traversal
current_question = None  # Track the current question's linkId for answer submission
pending_required_question = None  # Track the required question to return if unanswered

# TreeNode class for each question or group
class TreeNode:
    def __init__(self, data):
        self.link_id = data.get("linkId")
        self.text = data.get("text", "")
        self.type = data.get("type")
        self.required = data.get("required", False)
        self.enable_when = data.get("enableWhen", [])
        self.enable_behavior = data.get("enableBehavior", "all")  # Default to "all" if not specified
        self.answer_option = data.get("answerOption", [])
        self.children = [TreeNode(child) for child in data.get("item", [])]

# Build the tree structure for the questionnaire
def build_tree(data):
    return TreeNode(data)

# Initialize the questionnaire tree and stack
questionnaire_tree = build_tree({"linkId": "root", "item": questionnaire["item"]})
traversal_stack = [questionnaire_tree]  # Start traversal from the root

class Answer(BaseModel):
    answer: str

def load_answers():
    """Load answers from ANSWERS_FILE if it exists, else return an empty dictionary."""
    if os.path.exists(ANSWERS_FILE):
        with open(ANSWERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def is_question_enabled(node, answers):
    """
    Check if a question should be enabled based on the `enableWhen` conditions and stored answers.
    """
    if not node.enable_when:
        return True
    
    behavior_any = node.enable_behavior == "any"
    matches = []

    for condition in node.enable_when:
        question_id = condition["question"]
        expected_answer_string = condition.get("answerString")
        expected_answer_boolean = str(condition.get("answerBoolean")).lower()
        actual_answer = str(answers.get(question_id)).lower()

        match = (
            (expected_answer_string and actual_answer == expected_answer_string) or 
            (expected_answer_boolean is not None and actual_answer == expected_answer_boolean)
        )
        matches.append(match)

    return any(matches) if behavior_any else all(matches)

@app.get("/nextQuestion")
async def get_next_question():
    global traversal_stack, current_question, pending_required_question

    # Load answers from file
    answers = load_answers()

    # If there is a pending required question that is enabled but unanswered, return it
    if pending_required_question:
        pending_node = find_node(questionnaire_tree, pending_required_question)
        if pending_node and pending_node.type != "group" and is_question_enabled(pending_node, answers) and pending_node.link_id not in answers:
            current_question = pending_node.link_id
            return JSONResponse(content={
                "linkId": pending_node.link_id,
                "text": pending_node.text,
                "type": pending_node.type,
                "required": pending_node.required,
                "answerOption": pending_node.answer_option  # Include answer options if present
            })

    # Traverse until we find a node with a type, enabled, and optionally required, or exhaust the stack
    while traversal_stack:
        current_node = traversal_stack.pop()
        
        # Push children to the stack in reverse order for preorder traversal
        for child in reversed(current_node.children):
            traversal_stack.append(child)
        
        # Check if the current node has a `type` and is enabled
        if current_node.type and is_question_enabled(current_node, answers):
            current_question = current_node.link_id
            
            # If it's a question (not a group) and required but unanswered, set it as pending
            if current_node.required and current_node.type != "group" and current_node.link_id not in answers:
                pending_required_question = current_node.link_id
            else:
                pending_required_question = None  # Clear if no required question is pending

            # Prepare the response content
            response_content = {
                "linkId": current_node.link_id,
                "text": current_node.text,
                "type": current_node.type,
                "required": current_node.required,
            }
            
            # If the question type is choice, include answer options
            if current_node.type == "choice":
                response_content["answerOption"] = current_node.answer_option

            return JSONResponse(content=response_content)

    return JSONResponse(content={"message": "No more items"})

@app.post("/submit-answer")
async def submit_answer(answer: Answer):
    global current_question, pending_required_question

    # Ensure there’s a current question to answer
    if not current_question:
        raise HTTPException(status_code=404, detail="No current question available to answer.")

    # Load existing answers or initialize an empty dictionary
    answers = load_answers()

    # Save the answer for the current question
    answers[current_question] = answer.answer
    with open(ANSWERS_FILE, 'w') as f:
        json.dump(answers, f, indent=4)

    # Reset pending_required_question if the answered question matches it
    if pending_required_question == current_question:
        pending_required_question = None

    return {"message": "Answer received and stored."}

# Helper function to find a node by link_id
def find_node(node, link_id):
    if node.link_id == link_id:
        return node
    for child in node.children:
        result = find_node(child, link_id)
        if result:
            return result
    return None

# To run the app: `uvicorn filename:app --reload`
