# -*- coding: utf-8 -*-

import requests
import pandas as pd
import json

# This quick and dirty script aims at getting GitHub enterprise users details while exploring the GraphQL API.
# You can use Altair GraphQL Client to test and adapt the GraphQL queries.

# Github GraphQL endpoint and authentication
api_url = 'https://api.github.com/graphql'
# GitHub API token must have read:enterprise or admin:enterprise scope and user must be enterprise owner
api_token = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
headers = {'Authorization': 'bearer %s' % api_token}
enterprise_slug = "your-entreprise-slug"
"

######################################################
# First get list of users that are enterprise owners #
######################################################

# Dictionnary to store information about owners
# organizational_roles will contain membership and/or ownership
owners = { "login":[],
                  "name": [],
                  "email": []}

# GraphQL query for listing enterprise owners
owners_query = { 'query' : '''
query($enterpriseSlug: String!, $afterCursor: String) {
  enterprise(slug: $enterpriseSlug) {
    ownerInfo {
      admins(first:100, after: $afterCursor) {
        nodes {
          login         
          name
          email
        }
        pageInfo {
          endCursor
          startCursor
          hasNextPage
          hasPreviousPage        
        }
      }
    }
  }
}''',
'variables': {
    'enterpriseSlug': enterprise_slug, 
    'afterCursor': None
    },
}

# variables used for pagination
hasNextPage = True
endCursor = None

while hasNextPage:
    # use endCursor for paginating queries if necessary
    owners_query['variables']['afterCursor'] = endCursor
    # POST request
    r = requests.post(url=api_url, json=owners_query, headers=headers)
    api_data = r.json()
    # Get pagination information from the response
    endCursor = api_data["data"]["enterprise"]["ownerInfo"]["admins"]["pageInfo"]["endCursor"]
    hasNextPage = api_data["data"]["enterprise"]["ownerInfo"]["admins"]["pageInfo"]["hasNextPage"]
    # Get enterprise owners information
    owners_info = api_data["data"]["enterprise"]["ownerInfo"]["admins"]["nodes"]
    for o in owners_info:
        owners["login"].append(o["login"])
        owners["name"].append(o["name"])
        owners["email"].append(o["email"])

# Write resuts to a file to avoid repeating query when testing
with open('owners.json', 'w', encoding='utf8') as f:
    json.dump(owners, f, ensure_ascii=False)

##################################################################
# Then get list of users that are organization members or owners #
##################################################################

# Dictionnary to store information about members or owners
# organizational_roles will contain membership and/or ownership
members_roles = { "login":[],
                  "name": [],
                  "email": [],
                  "organizational_roles": [] }

# GraphQL query for listing enterprise members and their status in enterprise organizations
# Query explanation : get enterprises members as Union and get details using the EnterpriseUserAccount
# Warning : enterprise organizations will not be paginated. We assume the enterprise has less than 100 organizations

members_query = { 'query' : '''
query($enterpriseSlug: String!, $afterCursor: String) {
  enterprise(slug: $enterpriseSlug) {
    members(first:100, after: $afterCursor) {
      nodes {
        ... on EnterpriseUserAccount{
          organizations(first:100) {
            nodes{
              login
            }
            edges {
              role
            }
          }
          user {
            login
            name
            email
          }
        }
      }
      pageInfo {
        endCursor
        startCursor
        hasNextPage
        hasPreviousPage        
      }
    }
  }
}
''',
'variables': {
    'enterpriseSlug': enterprise_slug, 
    'afterCursor': None
    },
}

# variables used for pagination
hasNextPage = True
endCursor = None

while hasNextPage:
    # use endCursor for paginating queries if necessary
    members_query['variables']['afterCursor'] = endCursor
    # POST request
    r = requests.post(url=api_url, json=members_query, headers=headers)
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
        members_roles["name"].append(m["user"]["name"])
        members_roles["email"].append(m["user"]["email"])
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
oc_query = {
    'query': '''
query ($enterpriseSlug: String!, $afterCursor: String) {
  enterprise(slug: $enterpriseSlug) {
    ownerInfo {
      outsideCollaborators(first: 100, after: $afterCursor) {
        totalCount
        edges {
          repositories(first: 100) {
            nodes {
              nameWithOwner
            }
            edges {
              node {
                isPrivate
              }
            }
          }
          node {
            login
            name
            email
          }
        }
        pageInfo {
          endCursor
          startCursor
          hasNextPage
          hasPreviousPage        
        }
      }
    }
  }
}
''',
    'variables': {
        'enterpriseSlug': enterprise_slug,
        'afterCursor': None,
    },
}

# variables used for pagination
hasNextPage = True
endCursor = None

while hasNextPage:
    oc_query['variables']['afterCursor'] = endCursor
    # POST request
    r = requests.post(url=api_url, json=oc_query, headers=headers)
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
        oc_info["name"].append(oc["node"]["name"])
        oc_info["email"].append(oc["node"]["email"])
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
owners = pd.read_json('owners.json')
owners = owners.astype("string")

# add entreprise_roles column
oc_info['entreprise_roles'] = 'outside_collaborator'
members_roles.loc[members_roles['organizational_roles'].notnull(), 'entreprise_roles'] = 'member'
# Handle unafiliated case (only if not an owner)
members_roles.loc[(members_roles['organizational_roles'].isnull()) & (~members_roles['login'].isin(owners['login'])), 'entreprise_roles'] = 'unaffiliated'
# Mark enterprise owners - add comma only if user is already marked as member
owners_mask = members_roles['login'].isin(owners['login'])
members_roles.loc[owners_mask & (members_roles['entreprise_roles'] == 'member'), 'entreprise_roles'] = 'member,owner'
members_roles.loc[owners_mask & (members_roles['entreprise_roles'] != 'member'), 'entreprise_roles'] = 'owner'

# Split outside collaborators in two lists to deal with the case where member are also outside collaborators ...
oc_not_member = oc_info[~oc_info['login'].isin(members_roles['login'])]
oc_and_member = oc_info[oc_info['login'].isin(members_roles['login'])]

# concat member and outside collaborator that are not alreay members
result = pd.concat([members_roles, oc_not_member], ignore_index=True)

# Add outside collaboration information to members
result.loc[result['login'].isin(oc_and_member['login']), 'outside_collaborator_public_repos'] = result['login'].map(oc_and_member.set_index('login')['outside_collaborator_public_repos'])
result.loc[result['login'].isin(oc_and_member['login']), 'outside_collaborator_private_repos'] = result['login'].map(oc_and_member.set_index('login')['outside_collaborator_private_repos'])
result.loc[result['login'].isin(oc_and_member['login']), 'entreprise_roles'] += ",outside_collaborator"

# A enterprise license is taken by either
# - an enterprise owner
# - an organization member
# - an outside collaborator in a private repo 
result["enterprise_license_taken"] = 0
result.loc[result['entreprise_roles'].str.contains('owner'), 'enterprise_license_taken'] = 1
result.loc[result['entreprise_roles'].str.contains('member'), 'enterprise_license_taken'] = 1
result.loc[~result['outside_collaborator_private_repos'].isnull(), 'enterprise_license_taken'] = 1
print(str(result['enterprise_license_taken'].sum()) + " licences consommées")

# Introduce line break in repo list to display things nicely
result['outside_collaborator_public_repos'] = result['outside_collaborator_public_repos'].str.replace(',','\n')
result['outside_collaborator_private_repos'] = result['outside_collaborator_private_repos'].str.replace(',','\n')

# output everything to a csv file
result.to_csv("test.csv", index=False, encoding='utf-8')
