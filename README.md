# GitHub Management helpers

This repository hosts various scripts to help manage a GitHub enterprise account.

## list_users.py

An sample python script which queries the GitHub GraphQL API to list GitHub enterprise users details.  
In order to use it : set github `api_token` and replace `your-enterprise-slug` in the script with your GitHub enterprise slug.

## remove_untagged_imgs.py

Example to delete untagged containers from a repository inside an organization.  
To use it simply update the variables including the `api_token`.
