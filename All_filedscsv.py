import os
import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
import re
import getpass 

csv_path = r'C:\Users\SESA746606\Documents\TotalArchivalProjects\Projects_names.csv'
df = pd.read_csv(csv_path, encoding="utf-8")

for index, row in df.iterrows():
    project_id = row['Project_id']
    #project_name = re.sub(r'[^a-zA-Z0-9\\s]', '',row['Project_name'])
    project_name = row['Project_name']
    project_name = project_name.replace('/', '').replace(':', '').replace('"',' ').replace('<',' ').replace('>',' ')
    #project_name = project_name.replace('/', '_')
    print(project_name)


    url = 'http://10.236.34.9:8080/sr/jira.issueviews:searchrequest-csv-all-fields/temp/SearchRequest.csv?jqlQuery=project%3D{}'.format(project_id)
    username = input("Enter the Username:") 
    password = getpass.getpass("Enter the Password:")

    response = requests.get(url, auth=HTTPBasicAuth(username, password), verify=False)

    # Define the folder path based on the project key
    folder_path = r'C:\Users\SESA746606\OneDrive - Schneider Electric\KNX\Archival projects\{}'.format(project_name)

    # Create the folder if it doesn't exist
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # Save the CSV file in the created folder
    file_path = os.path.join(folder_path, '{}.csv'.format(project_name))
    with open(file_path, 'wb') as file:
        file.write(response.content)
