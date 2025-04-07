#!/usr/bin/python3

import requests
import json
import os

API_KEY = os.environ.get("IMMICH_API_KEY")
SERVER_URL = os.environ.get("IMMICH_SERVER_URL")
SHARED_FOLDER = os.environ.get("PHOTOS_SHARED_FOLDER")
SHARED_IMMICH_FOLDER = os.environ.get("IMMICH_SHARED_FOLDER")

if API_KEY is None:
    print("PATH environment variable not found.")
    exit(1)


def file_exists_in_folder(folder_path, filename):
    for root, dirs, files in os.walk(folder_path):
        if filename in files:
            return True
    return False

def immich_api_request(action, endpoint, payload={}):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': API_KEY
    }
    return requests.request(action, SERVER_URL + endpoint, headers=headers, data=payload)

def delete_asset_ids(ids):
    if len(ids) == 0:
        return
    print(f"Deleting {len(ids)} assets...")
    payload = {
        "force": True,
        "ids": ids
    }
    response = immich_api_request("DELETE", "/api/assets", json.dumps(payload))
    print(response.text)

current_page = 1

while current_page is not None:
    print(f"Fetching page {current_page}...")

    payload = json.dumps({
        "page": current_page,
        "size": 500,
        "withArchived": False,
        "withDeleted": False,
    })
    response = immich_api_request("POST", "/api/search/metadata", payload)
    search_result = json.loads(response.text)

    asset_list = search_result["assets"]["items"]
    next_page = search_result["assets"]["nextPage"]
    if current_page == next_page:
         break
    current_page = next_page


    duplicated_assets_id = []
    duplicate_files = []
    for asset in asset_list:
        asset_file = asset["originalFileName"]
        if asset["libraryId"] == "ccf1e8f5-2631-4139-96a2-61cdc36421d9":
            continue
        if SHARED_IMMICH_FOLDER in asset["originalPath"]:
            continue
        is_shared_resource = file_exists_in_folder(SHARED_FOLDER, asset_file)
        if not is_shared_resource:
            continue
        print(f"{asset_file} exists in shared resource!")
        duplicated_assets_id.append(asset["id"])
        duplicate_files.append(asset["originalPath"])

    delete_asset_ids(duplicated_assets_id)
