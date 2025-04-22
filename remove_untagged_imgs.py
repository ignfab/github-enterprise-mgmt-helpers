# -*- coding: utf-8 -*-

import sys
from urllib3.util import Retry
from requests import Session
from requests.adapters import HTTPAdapter

# A basic script to remove untagged images from a GitHub repository packages registry

# Use a retry strategy
s = Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 502, 503, 504],
    allowed_methods={'GET','DELETE'},
)
s.mount('https://', HTTPAdapter(max_retries=retries))

#############
# Variables #
#############

# GitHub organization
org = "ignfab"
# GitHub project in organization
project = "minalac-generator"
# Array to store container to delete
ids_to_delete = []
# Github REST API endpoint
api_root = ' https://api.github.com'
# GitHub API token must have read:packages and delete:packages scope
api_token = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# Pass token in header
headers = {'Authorization': 'bearer %s' % api_token}
# Results per GitHub API result page
results_per_page=100

#########
# Logic #
#########

# Get untagged containers package id to delete
def get_ids_from_result(requests_resp):
    json_resp = r.json()
    for v in json_resp:
        if not v["metadata"]["container"]["tags"]:
            ids_to_delete.append(v["id"])

# get containers list
url = api_root + \
    f"/orgs/{org}/packages/container/{project}/versions?state=active&per_page={results_per_page}"
r = s.get(url, headers=headers)
# get ids to delete
get_ids_from_result(r)
# get remaining results if they exists
while ("next" in r.links):
    next_url = r.links["next"]["url"]
    r = s.get(next_url, headers=headers)
    get_ids_from_result(r)

print(str(len(ids_to_delete)) + " untagged containers will be deleted")

# Delete untagged container packages
for id in ids_to_delete:
    deletion_url = api_root + f"/orgs/{org}/packages/container/{project}/versions/{id}"
    r = s.delete(deletion_url, headers=headers)
    if (r.status_code != 204):
        print("Error deleting " + str(id))
        sys.exit(1)
    else:
        print(str(id) + " deleted succesfully")
