from jira import JIRA
from jira.exceptions import JIRAError
import requests
from io import BytesIO

try:
    # --- Connect to source (Server) and target (Data Center) ---
    server_options = {'server': 'http://48.200.96.84:8080/', 'verify': False}
    dc_options = {'server': 'http://4.155.39.18:8080/', 'verify': False}

    # Use basic_auth with proper credentials
    server_jira = JIRA(options=server_options, basic_auth=('admin', 'admin'))
    dc_jira = JIRA(options=dc_options, basic_auth=('sesa2026', 'admin'))
    
    print("✓ Successfully connected to both JIRA instances")

except JIRAError as e:
    print(f"✗ Authentication failed: {e}")
    print("Please verify:")
    print("  - Server URLs are correct")
    print("  - Usernames and passwords are correct")
    print("  - If using API tokens, ensure token is valid and not expired")
    exit(1)

# --- Example: migrate one project ---
project_key = "TEST"  # Change this to a valid project key

try:
    # List available projects to verify KEY exists
    print(f"\nSearching for issues in project: {project_key}")
    issues = server_jira.search_issues(f'project={project_key}', maxResults=50)
    print(f"✓ Found {len(issues)} issues in project {project_key}\n")

except JIRAError as e:
    print(f"✗ Project not found or error: {e}")
    print("Available projects:")
    projects = server_jira.projects()
    for proj in projects:
        print(f"  - {proj.key}: {proj.name}")
    exit(1)

try:
    # First, verify project exists in Data Center
    dc_projects = {p.key: p.name for p in dc_jira.projects()}
    if project_key not in dc_projects:
        print(f"✗ Project '{project_key}' not found in Data Center")
        if dc_projects:
            print(f"Available projects: {', '.join(dc_projects.keys())}")
        else:
            print("No projects exist in Data Center yet.")
        print(f"\n→ Please create project '{project_key}' in Data Center first, then run again.")
        exit(1)
    
    print(f"✓ Found project '{project_key}' in Data Center\n")
    
    for issue in issues:
        # Prepare issue data with required fields
        issue_dict = {
            'project': project_key,  # Send project key as string, not dict
            'summary': issue.fields.summary,
            'description': issue.fields.description or '',
            'issuetype': issue.fields.issuetype.name,  # Send issuetype name as string
        }

        # Create issue in Data Center
        new_issue = dc_jira.create_issue(fields=issue_dict)
        print(f"✓ Migrated {issue.key} -> {new_issue.key}")
        
        # Migrate attachments
        if issue.fields.attachment:
            print(f"  Migrating {len(issue.fields.attachment)} attachment(s)...")
            for attachment in issue.fields.attachment:
                try:
                    # Download attachment from source
                    response = requests.get(attachment.content, verify=False)
                    attachment_content = BytesIO(response.content)
                    
                    # Upload to target
                    dc_jira.add_attachment(issue=new_issue.key, attachment=attachment_content, filename=attachment.filename)
                    print(f"    ✓ {attachment.filename}")
                except Exception as e:
                    print(f"    ✗ Failed to migrate {attachment.filename}: {e}")
        else:
            print(f"  (No attachments)")
        
        print()
        
except JIRAError as e:
    print(f"✗ Error: {e}")