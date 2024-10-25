import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

# Install FastAPI and uvicorn if not already installed:
# pip install fastapi uvicorn

# Read the JSON file
with open('data.json', 'r') as file:
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

# Build the index
linkid_index = build_linkid_index(questionnaire.get('item', []))

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

# To run the app, use the command:
# uvicorn filename:app --reload
