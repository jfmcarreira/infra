#!/usr/bin/python3

import requests
import json
import os
import datetime
import subprocess
import collections

PRINT_ASSET_INFO = False
API_KEY = os.environ.get("IMMICH_API_KEY")
GPHOTOS_DIR = os.environ.get("GPHOTOS_DIR")
SERVER_URL = "https://immich.jcarreira.pt"
SHARED_FOLDER = "/media/photos/"

API_KEY = os.environ.get("IMMICH_API_KEY")
SERVER_URL = os.environ.get("IMMICH_SERVER_URL")
SHARED_FOLDER = os.environ.get("PHOTOS_SHARED_FOLDER")
SHARED_IMMICH_FOLDER = os.environ.get("IMMICH_SHARED_FOLDER")

if API_KEY is None:
    print("API_KEY environment variable not found.")
    exit(1)

if GPHOTOS_DIR is None:
    print("GPHOTOS_DIR environment variable not found.")
    exit(1)

current_time = datetime.datetime.now()
search_start_time = current_time - datetime.timedelta(days=30)
search_start_time_str = search_start_time.strftime("%Y-%m-%d") + "T00:00:00.000Z"

def immich_api_request(action, endpoint, payload={}):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-api-key': API_KEY
    }
    return requests.request(action, SERVER_URL + endpoint, headers=headers, data=payload)

response = immich_api_request("GET", "/api/albums?shared=true")
album_list_json = json.loads(response.text)
album_list = []
album_list_ids = {}
for album in album_list_json:
    name = album["albumName"]
    album_list.append(name)
    album_list_ids[name] = album["id"]

print(f"Using the following Google Photos dir {GPHOTOS_DIR}")

gphotos_sync_command = [
    os.path.expanduser("~/.local/bin/gphotos-sync"),
    "--use-flat-path",
    "--omit-album-date",
    GPHOTOS_DIR,
]
subprocess.run(gphotos_sync_command)

def file_exists_in_gphotos_album(filename):
    albuns = []
    for root, dirs, album_files in os.walk(GPHOTOS_DIR + "/albums"):
        for file in album_files:
            if filename in file:
                folder_name = os.path.basename(root)
                albuns.append(folder_name)
                break
    return albuns

def search_immich_album(gphoto_album):
    if gphoto_album is None:
         return None

    processed_gphoto_album = gphoto_album.replace(" ", "_")
    for album in album_list:
        if gphoto_album == album:
            return album
        if processed_gphoto_album == album:
            return album
    return None


current_page = 1
while current_page is not None:
    payload = json.dumps({
        "page": current_page,
        "size": 100,
        "withArchived": False,
        "withDeleted": False,
        "takenAfter": search_start_time_str
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
    album_assets = collections.defaultdict(list)
    for asset in asset_list:
        asset_file = asset["originalFileName"]

        if PRINT_ASSET_INFO:
            print(asset["originalFileName"])
            print(asset["fileCreatedAt"])

        if SHARED_IMMICH_FOLDER in asset["originalPath"]:
            continue

        google_album_names = file_exists_in_gphotos_album(asset_file)
        for google_album in google_album_names:
            immich_album = search_immich_album(google_album)
            if immich_album is None:
                continue
            if PRINT_ASSET_INFO:
                print(f"Add {asset_file} to album {immich_album}")
            album_assets[immich_album].append(asset["id"])

    for album, assets in album_assets.items():
        if PRINT_ASSET_INFO:
            print(f"Add {len(assets)} to album {album}")
        immich_album_id = album_list_ids[immich_album]
        payload = json.dumps({"ids": assets})
        immich_api_request("PUT", f"/api/albums/{immich_album_id}/assets", payload)