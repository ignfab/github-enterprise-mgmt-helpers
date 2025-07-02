# -*- coding: utf-8 -*-

import requests
import csv
import sys
import pandas as pd
import numpy as np
import json

# This quick and dirty script aims at getting GitHub enterprise users details
# You can use Altair GraphQL Client to test and adapt the GraphQL queries

# Github GraphQL endpoint and authentication
url = 'https://api.github.com/graphql'
# GitHub API token must have read:enterprise or admin:enterprise scope and user must be enterprise owner
api_token = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
headers = {'Authorization': 'bearer %s' % api_token}
entreprise_slug = "your-entreprise-slug"

##################################################################
# First get list of users that are organization member or owners #
##################################################################

# Dictionnary to store information about members
# organizational_roles will contain membership and/or ownership
members_roles = { "login":[],
                  "name": [],
                  "email": [],
                  "organizational_roles": [] }

# GraphQL query for listing enterprise members and their status in enterprise organizations
# Query explanation : get enterprises members as Union and get details using the EnterpriseUserAccount
# Warning : enterprise organizations will not be paginated. We assume the enterprise has less than 100 organizations

members_query = { 'query' : f'''
query {{
  enterprise(slug: "{entreprise_slug}") {{
    members(first:100, after: null) {{
      nodes {{
        ... on EnterpriseUserAccount{{
          organizations(first:100) {{
            nodes{{
              login
            }}
            edges {{
              role
            }}
          }}
          user {{
            login
            name
            email
          }}
        }}
      }}
      pageInfo {{
        endCursor
        startCursor
        hasNextPage
        hasPreviousPage        
      }}
    }}
  }}
}}
'''}

# variables used for pagination
hasNextPage = True
endCursor = None

while hasNextPage:
    paginated_query = members_query
    # use endCursor for paginating queries if necessary
    if endCursor:
        paginated_query["query"] = paginated_query["query"].replace('null','"'+endCursor+'"')
    # POST request
    r = requests.post(url=url, json=paginated_query, headers=headers)
    api_data = r.json()
    # Get pagination information from the response
    endCursor = api_data["data"]["enterprise"]["members"]["pageInfo"]["endCursor"]
    hasNextPage = api_data["data"]["enterprise"]["members"]["pageInfo"]["hasNextPage"]
    # Get enterprise members information
    members_info = api_data["data"]["enterprise"]["members"]["nodes"]
    for m in members_info:
        orgs = [o["login"] for o in m["organizations"]["nodes"]]
        roles = [o["role"] for o in m["organizations"]["edges"]]
        organizational_roles = [':'.join([o,r]) for o, r in zip(orgs, roles)]
        members_roles["login"].append(m["user"]["login"])
        if m["user"]["name"]:
            members_roles["name"].append(m["user"]["name"])
        else:
            members_roles["name"].append(None)
        if m["user"]["email"]:
            members_roles["email"].append(m["user"]["email"])
        else:
            members_roles["email"].append(None)
        if organizational_roles:
            members_roles["organizational_roles"].append(','.join(organizational_roles))
        else:
            members_roles["organizational_roles"].append(None)

# Write resuts to a file to avoid repeating query when testing
with open('members_roles.json', 'w', encoding='utf8') as f:
    json.dump(members_roles, f, ensure_ascii=False)

############################################################
# Then get list of GitHub Enterprise outside collaborators #
############################################################

# Dictionnary to store information about outside collaborators
# outside_collaborator_public_repos will contain list of public repo the user is a member of
# outside_collaborator_private_repos will contain list of private repo the user is a member of
oc_info = { "login":[],
            "name": [],
            "email": [],
            "outside_collaborator_public_repos":[], 
            "outside_collaborator_private_repos":[] }

# GraphQL query for listing enterprise outside collaborators and the repositories they are members of
# Query explanation : Using the ownerInfo object get list of outside collaborators then for each get list of repositories they are member of
oc_query = { 'query' : f'''
query {{
  enterprise(slug: "{entreprise_slug}") {{
    ownerInfo {{
      outsideCollaborators(first:100 after: null) {{
        totalCount
        edges {{
          repositories(first:100) {{
            nodes{{
              nameWithOwner
            }}
            edges {{
              node{{
                isPrivate
              }}
            }}
          }}
          node {{
            login
            name
            email
          }}
        }}
        pageInfo {{
          endCursor
          startCursor
          hasNextPage
          hasPreviousPage        
        }}
      }}
    }}
  }}
}}
''' }

# variables used for pagination
hasNextPage = True
endCursor = None

while hasNextPage:
    paginated_query = oc_query
    # use endCursor for paginating queries if necessary
    if endCursor:
        paginated_query["query"] = paginated_query["query"].replace('null','"'+endCursor+'"')
    # POST request
    r = requests.post(url=url, json=paginated_query, headers=headers)
    api_data = r.json()
    # Get pagination information from response
    endCursor = api_data["data"]["enterprise"]["ownerInfo"]["outsideCollaborators"]["pageInfo"]["endCursor"]
    hasNextPage = api_data["data"]["enterprise"]["ownerInfo"]["outsideCollaborators"]["pageInfo"]["hasNextPage"]
    # Get outside collaborators information
    outside_collab_info = api_data["data"]["enterprise"]["ownerInfo"]["outsideCollaborators"]["edges"]
    for oc in outside_collab_info:
        repository = [x["nameWithOwner"] for x in oc["repositories"]["nodes"]]
        private = [x["node"]["isPrivate"] for x in oc["repositories"]["edges"]]
        private_repos = ','.join([repository[i] for i, x in enumerate(private) if x])
        public_repos = ','.join([repository[i] for i, x in enumerate(private) if not x])
        oc_info["login"].append(oc["node"]["login"])
        if oc["node"]["name"]:
            oc_info["name"].append(oc["node"]["name"])
        else: 
            oc_info["name"].append(None)
        if oc["node"]["email"]:
            oc_info["email"].append(oc["node"]["email"])
        else:
            oc_info["email"].append(None)
        if public_repos:
            oc_info['outside_collaborator_public_repos'].append(public_repos)
        else:
            oc_info['outside_collaborator_public_repos'].append(None)
        if private_repos:
            oc_info['outside_collaborator_private_repos'].append(private_repos)
        else:
            oc_info['outside_collaborator_private_repos'].append(None)

# Write resuts to a file to avoid repeating query when testing
with open('oc_info.json', 'w', encoding='utf8') as f:
    json.dump(oc_info, f, ensure_ascii=False)

###########################################
# Tidy up everything with a bit of pandas #
###########################################

# Load datasets
oc_info = pd.read_json('oc_info.json')
oc_info = oc_info.astype("string")
members_roles = pd.read_json('members_roles.json')
members_roles = members_roles.astype("string")

# add entreprise_roles column
oc_info['entreprise_roles'] = 'outside_collaborator'
members_roles['entreprise_roles'] = 'member'

# Output the number of licenses already taken
# A license is used by a member or by an outside collaborator in a private repo 
private_collab = oc_info[~oc_info['outside_collaborator_private_repos'].isnull()]
private_collab_not_members = private_collab[~private_collab['login'].isin(members_roles['login'])]
print(str(members_roles.shape[0]+private_collab_not_members.shape[0]) + " licences consommées")

# Split outside collaborators in two lists to deal with the case where member are also outside collaborators ...
oc_not_member = oc_info[~oc_info['login'].isin(members_roles['login'])]
oc_and_member = oc_info[oc_info['login'].isin(members_roles['login'])]

# concat member and outside collaborator that are not alreay members
result = pd.concat([members_roles, oc_not_member], ignore_index=True)

# Add outside collaboration information to members
result.loc[result['login'].isin(oc_and_member['login']), 'outside_collaborator_public_repos'] = result['login'].map(oc_and_member.set_index('login')['outside_collaborator_public_repos'])
result.loc[result['login'].isin(oc_and_member['login']), 'outside_collaborator_private_repos'] = result['login'].map(oc_and_member.set_index('login')['outside_collaborator_private_repos'])
result.loc[result['login'].isin(oc_and_member['login']), 'entreprise_roles'] = "member,outside_collaborator"

# A enterprise license is taken by a member or by an outside collaborator in a private repo 
result["enterprise_license_taken"] = 0
result.loc[result['entreprise_roles'].str.contains('member'), 'enterprise_license_taken'] = 1
result.loc[~result['outside_collaborator_private_repos'].isnull(), 'enterprise_license_taken'] = 1

# Introduce line break in repo list to display things nicely
result['outside_collaborator_public_repos'] = result['outside_collaborator_public_repos'].str.replace(',','\n')
result['outside_collaborator_private_repos'] = result['outside_collaborator_private_repos'].str.replace(',','\n')

# output everything to an excel file
result.to_excel("test.xlsx", index=False)
