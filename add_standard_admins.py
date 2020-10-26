import getopt
import json
import requests
import sys
from dataclasses import dataclass
from getpass import getpass


@dataclass
class orgData:
    '''Class for organization level data. Mostly to add menu number.'''

    id: str
    name: str
    menu: int


def print_user_text(message):
    '''
    Prints a line of text meant for the user to read.

    :param message: Line of text

    :return: None
    '''
    print(f'@ {message}')


def print_help():
    '''
    Print help text.

    :return: None
    '''
    print_user_text('')
    print_user_text('To run the script, enter:')
    print_user_text('python pushRfProfiles.py -o <org name>')
    print_user_text('')
    print_user_text('-o can be a partial name in quotes')
    print_user_text('such as \'Calla\' or \'ssouri\'.')
    print_user_text('Use /all for all organizations you have access to.')
    print_user_text('')
    print_user_text('Use double quotes (/"") in Windows to pass arguments')
    print_user_text('containing spaces.')
    print_user_text('')


def get_org_list(api_key):
    '''
    Return the organizations' list for a specified admin.
    
    :param api_key: Meraki Dashboard API key

    :return: List of dictionaries containing all organizations your API key can access.
    '''
    
    url = f'https://api-mp.meraki.com/api/v0/organizations/'
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    r = requests.request('GET', url, headers=headers)

    if r.status_code == '401':
        print_user_text("Invalid API key.")
        sys.exit(1)

    rjson = r.json()

    return(rjson)

def get_admin_list(api_key, org_id):
    #returns the organizations' list for a specified admin
    '''
    Return the admins for a specific organization.
    
    :param api_key: Meraki Dashboard API key
    :param org_id: Organization ID

    :return: List of dictionaries containing the org's admins.
    '''
    
    url = f'https://api-mp.meraki.com/api/v0/organizations/{org_id}/admins'
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    r = requests.request('GET', url, headers=headers)

    if r.status_code == '401':
        print_user_text("Invalid API key.")
        sys.exit(1)

    rjson = r.json()

    return(rjson)


def choose_org(org_list):
    '''
    Print a menu, then return user's chosen organization.
    
    :param org_list: List of dicts of Meraki organizations
    
    :return: List of dicts containing matching org.
    '''

    chosen_org = ''

    while chosen_org == '':
        for org in org_list:
            print(f'{org.menu}: {org.name}')
        chosen_org = input("Enter Q to quit or select menu number: ")

        if chosen_org.lower() == 'q':
            print("Quiting program...")
            sys.exit()
        else:
            for org in org_list:
                if org.menu == int(chosen_org):
                    return([org])
            # If no org matches, print notice then loop.
            print(f'No matching menu item {chosen_org}\n')
            chosen_org == ''


def post_org_admin(api_key, org_id, admin_email, admin_name, admin_privilege):
    '''
    Create new administrator on an organization..
    
    :param api_key: Meraki Dashboard API key
    :param org_id: Organization ID number
    :param admin_email: String containing admin account's email
    :param admin_name: String containing admin account's name
    :param admin_privilege: String containing admin account's privilege level

    :return: requests.Response object
    '''

    url = f'https://api-mp.meraki.com/api/v0/organizations/{org_id}/admins'
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    json_payload = json.dumps({'name': admin_name, 'email': admin_email, 'orgAccess': admin_privilege})
    r = requests.request('POST', url, headers=headers, data=json_payload)

    if r.status_code == 400:
        print(f"WARNING: {admin_email} already registered with a Cisco Meraki Dashboard account, but unverified.\nUser must verify their email address before administrator permissions can be granted.")
    elif r.status_code != 201:
        print(f"{admin_email} attempt returned status code: {r.status_code}\n")
    else:
        print(f"{admin_email} added successfully.")

    return(r)


def filter_org_list(api_key, filter, org_list):
    '''
    Try to match a list of org IDs to a filter expression.

    :param api_key: Meraki Dashboard API key
    :param filter: '/all' for all orgs or a string for finding partial matches
    :param org_list: List of dicts containing Meraki organizations

    :return: List of dicts containing organizations that match filter, sorted alphabetically.
    '''
    
    return_list = []
    process_all = False

    if filter == '/all':
        process_all = True

    # Add a number to make menu-making simpler
    menu_num = 1

    # Sort by org name
    sorted_orgs = sorted(org_list, key=lambda org_list: org_list['name'])
    
    for org in sorted_orgs:
        if process_all:
            return_list.append(orgData(org['id'], org['name'], menu_num))
            menu_num += 1
        else:
            # Check if the filter string exists in the org's name. A return of -1 means 'no'.
            # If it exists, create the object and add to the return list.
            if (org['name'].lower()).find(filter) != -1:
                return_list.append(orgData(org['id'], org['name'], menu_num))
                menu_num += 1

    # If any matches are found, len(return_list) will exist.
    if len(return_list):
        return(return_list)
    else:
        print_user_text(f'ERROR: No organizations matching: {filter}')
        sys.exit(1)

def main(argv):
    # Initialize variables for command line arguments
    arg_org_name = ''

    # Get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'ho:')
    except getopt.GetoptError:
        print_user_text('Error getting opts.')
        sys.exit(2)

    if opts:
        for opt, arg in opts:
            if opt == '-h':
                print_help()
                sys.exit()
            elif opt == '-o':
                if arg == '':
                    print_user_text('No org name')
                    sys.exit()
                else:
                    arg_org_name = arg.lower()

    else:
        print_user_text("No opts given.")
        print_help()
        sys.exit()

    # Use getpass() to hide API key cuz you have manners
    arg_api_key = getpass("API key: ")

    # Get your organization list and check if your API key works.
    raw_org_list = get_org_list(arg_api_key)

    # Match list of orgs to org filter
    filtered_orgs = filter_org_list(arg_api_key, arg_org_name, raw_org_list)

    if len(filtered_orgs) >= 0:
        matched_orgs = choose_org(filtered_orgs)
    else:
        print("\nRunning against all orgs...")
        matched_orgs = filtered_orgs

    # Org ID for the standard organization
    standard_org_id = "REPLACE WITH YOUR ORG ID"
    # Get admin list from standard org
    standard_admins = get_admin_list(arg_api_key, standard_org_id)

    # For each org that matched
    for org in matched_orgs:
        # Add each admin from the standard organization
        for admin in standard_admins:
            post_org_admin(arg_api_key, org.id, admin['email'], admin['name'], admin['orgAccess'])

if __name__ == '__main__':
    main(sys.argv[1:])
