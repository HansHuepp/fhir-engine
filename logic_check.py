import json

def get_item(session_id: str, item_id: str) -> str:
    # Read the JSON file
    try: 
        with open(f'{session_id}_answers.json', 'r') as file:
            answers = json.load(file)
    except Exception:
        raise KeyError

    return answers.get(item_id)

def check_item_value(session_id: str, item_id: str, operator: str, answerString: str, answerBoolean: bool):
    """
    check if the given item satisfies the condition, e.g. = "Ja"
    """
    # Read the JSON file
    with open(f'{session_id}_answers.json', 'r') as file:
        answers = json.load(file)
    try:
        answer = answers[item_id]
    except KeyError as e:
        print(f"KeyError: {e}")
        return False
    
    if operator == "=":
        if answerString is not None:
            return answer == answerString
        else:
            return answer == answerBoolean
    else:
        raise ValueError("Invalid operator for non-numeric data; use '=' or '!=' only")
    
def find_linkid(session_id: str, linkid):
    """
    Recursively search for a specific linkId in nested JSON data.
    
    Args:
        data (dict or list): The JSON data to search.
        linkid (str): The target linkId to find.
        
    Returns:
        dict: The dictionary with the matching linkId, or None if not found.
    """
    with open(f'{session_id}_answers.json', 'r') as file:
        answers = json.load(file)
    
    if isinstance(answers, dict):
        # Check if this dictionary has the target linkId
        if answers.get("linkId") == linkid:
            return answers
        # Otherwise, check each value to continue the search
        for key, value in answers.items():
            result = find_linkid(value, linkid)
            if result is not None:
                return result
    elif isinstance(answers, list):
        # Recursively check each item in the list
        for item in answers:
            result = find_linkid(item, linkid)
            if result is not None:
                return result
    return None