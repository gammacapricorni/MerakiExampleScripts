import sys
import getopt
import requests
import json
import time
from dataclasses import dataclass
from datetime import datetime
from getpass import getpass

# Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

# Connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 30
REQUESTS_READ_TIMEOUT = 30

# Used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now()

LINE_SEPARATOR = '-' * 20


@dataclass
class c_orgData:
    id: str
    name: str
    menu: int


def print_user_text(p_message):
    """
    Prints a line of text meant for the user to read.
    :param p_message: Line of text
    :return: None
    """

    print('@ %s' % p_message)
    return None


def print_help():
    """
    Prints help text for user.
    :return: None
    """
    print_user_text('')
    print_user_text('Use to update pre-existing Meraki Org with the standard set of admins')
    print_user_text('')
    print_user_text('merakirequestthrottler(), get_org_list(), filterorglist(), method of getting')
    print_user_text('opts, general approach to Meraki API/requests model use are based off')
    print_user_text('manageadmins.py at')
    print_user_text('https://github.com/meraki/automation-scripts/blob/master/manageadmins.py')
    print_user_text('by users mpapazog and shiyuechengineer, retrieved 10/19/2018 by Nash King')
    print_user_text('')
    print_user_text('To run the script, enter:')
    print_user_text('python standardAdmins.py -o <org>')
    print_user_text('')
    print_user_text('-o can be a partial name in quotes with a single wildcard, such as "Calla*"')
    print_user_text('')
    print_user_text('Use double quotes (\"\") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    print_user_text('')


def merakirequestthrottler(p_requestcount=1):
    """
    Ensures there is enough time between API requests to Dashboard, to avoid hitting shaper.
    :param p_requestcount:
    :return: None
    """
    global LAST_MERAKI_REQUEST

    if (datetime.now() - LAST_MERAKI_REQUEST).total_seconds() < (API_EXEC_DELAY * p_requestcount):
        time.sleep(API_EXEC_DELAY * p_requestcount)

    LAST_MERAKI_REQUEST = datetime.now()
    return None


def get_org_list(p_apikey):
    """
    Pulls list of all orgs the API key has access to.
    :param p_apikey: Your API key
    :return: list of dicts containing org info
    """

    merakirequestthrottler()

    try:
        r = requests.get('https://api.meraki.com/api/v0/organizations',
                         headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},
                         timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        print_user_text('ERROR 01: Unable to contact Meraki cloud')
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        return [{'id': 'null'}]

    rjson = r.json()

    return (rjson)


def get_admin_list(p_apikey, p_orgid):
    """
    Returns the list of organizations an the API key can access.

    :param p_apikey:
    :param p_orgid:
    :return: list of dicts
    """

    merakirequestthrottler()
    try:
        r = requests.get(f'https://api-mp.meraki.com/api/v0/organizations/{p_orgid}/admins',
                         headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},
                         timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except requests.exceptions.RequestException as e:
        print_user_text(f'Error: {e}')
        print_user_text('Unable to get list of administrators from organization.')
        sys.exit(1)

    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id': 'null'})
        return returnvalue

    rjson = r.json()

    return (rjson)


# Print menu of possible matching organizations
def print_org_menu(p_orglist):
    """
    Print menu of organizations.

    :param p_orglist: list of c_orgdata objects
    :return: single matching c_orgdata object
    """

    menu_choice = ''

    print('\nChoose organization from list, or Q to Quit')

    # Loop til menu_choice is a valid response or a valid org is chosen
    while menu_choice == '':
        for org in p_orglist:
            # Print each org
            print(f'{org.menu}: {org.name}')
        print('Q: Quit program')
        menu_choice = input('Enter choice: ')
        print('')
        if menu_choice.lower().strip() == 'q':
            sys.exit()

        # Check if menu_choice is not empty
        elif menu_choice != '' and menu_choice.isdigit():
            for org in p_orglist:
                # If org.menu matches, then return org
                if org.menu == int(menu_choice):
                    return org
            # If nothing matches, set menu_choice to empty to keep looping
            print('Invalid choice. Please try again.')
            menu_choice = ''
        else:
            print('Invalid choice. Please try again.')
            menu_choice = ''


def add_org_admin(p_apikey, p_orgid, p_email, p_name, p_privilege):
    """
    Creates admin for a single organization
    :param p_apikey: Your API key
    :param p_orgid: org ID
    :param p_email: administrator's email address - serves as user name
    :param p_name: administrator's display name
    :param p_privilege: privilege level. Full (read/write) or read-only
    :return:
    """
    merakirequestthrottler()

    try:
        r = requests.post(f'https://api-mp.meraki.com/api/v0/organizations/{p_orgid}/admins',
                          data=json.dumps({'name': p_name, 'email': p_email, 'orgAccess': p_privilege}),
                          headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},
                          timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except requests.exceptions.RequestException as e:
        print_user_text(f'Error msg: {e}')
        print_user_text(f'Unable to add administrator {p_email} to org.')
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        if r.status_code == 400:
            print_user_text(
                f'WARNING: {p_email} may already be added to org. If not, have user login to dashboard.meraki.com'
                'and verify their email address.')

    return (r.status_code)


def filterOrgList(p_apikey, p_filter, p_orglist):
    """
    :param p_apikey: Your API key.
    :param p_filter: Specified filter string. /all matches all orgs.
    :param p_orglist: Raw list of organizations from Get Organizations.
    :return: return_list: sorted filtered list of c_orgdata objects

    Tries to match a list of org IDs to a filter expression, then convert JSON into c_orgdata objects.
    """

    global start_section
    return_list = []

    flag_process_all = False
    flag_got_wildcard = False
    if p_filter == '/all':
        flag_process_all = False
        print("No /all allowed on admin adds.")
    else:
        wildcard_pos = p_filter.find('*')

        if wildcard_pos > -1:
            flag_got_wildcard = True
            start_section = ''
            end_section = ''

            if wildcard_pos == 0:
                # wildcard at start of string, only got end_section
                end_section = p_filter[1:]

            elif wildcard_pos == len(p_filter) - 1:
                # wildcard at start of string, only got start_section
                start_section = p_filter[:-1]
            else:
                # wildcard at middle of string, got both start_section and end_section
                wild_card_split = p_filter.split('*')
                start_section = wild_card_split[0]
                end_section = wild_card_split[1]

    for org in p_orglist:
        if flag_process_all:
            return_list.append(c_orgData(org['id'], org['name'], 0))
        elif flag_got_wildcard:
            flag_got_match = True
            # match start_section and end_section
            start_len = len(start_section)
            end_len = len(end_section)

            if start_len > 0:
                if org['name'][:start_len] != start_section:
                    flag_got_match = False
            elif end_len > 0:
                if org['name'][-end_len:] != end_section:
                    flag_got_match = False

            if flag_got_match:
                return_list.append(c_orgData(org['id'], org['name'], 0))

        else:
            # match full name
            if org['name'] == p_filter:
                return_list.append(c_orgData(org['id'], org['name'], 0))

    # Sort list here, so the right menu num gets added
    sorted_orgs = []
    sorted_orgs = sorted(return_list, key=lambda c_orgdata: c_orgdata.name)
    menu_num = 1
    for org in sorted_orgs:
        org.menu = menu_num
        menu_num += 1
    return (sorted_orgs)


def main(argv):
    # initialize variables for command line arguments
    arg_apikey = getpass('API key: ')
    arg_orgname = ''

    if arg_apikey == '':
        arg_apikey = getpass('Enter API key: ')

    # get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'ho:')
    except getopt.GetoptError:
        print_user_text('Error getting opts.')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print_help()
            sys.exit()
        elif opt == '-o':
            arg_orgname = arg
            if arg_orgname == '':
                print_user_text('No org name')
                sys.exit(2)

    # get list org all orgs belonging to this admin
    raw_org_list = get_org_list(arg_apikey)
    if raw_org_list[0]['id'] == 'null':
        print_user_text('ERROR: Error retrieving organization list')
        sys.exit(2)

    # match list of orgs to org filter
    matched_orgs = filterOrgList(arg_apikey, arg_orgname, raw_org_list)

    # if no orgs matching - NK 2018-08-23
    if not matched_orgs:
        print_user_text(f'Error: No organizations matching {arg_orgname}')
        sys.exit(2)

    # Print menu of possible matches
    print_org_menu(matched_orgs)

    # Org ID for the standard organization
    standard_msp_org = "PUT DEFAULT ORG ID HERE"

    # Get admin list from standard org
    standard_admins = get_admin_list(arg_apikey, standard_msp_org)

    # For each org that matched
    for org in matched_orgs:
        # Add each admin from the standard organization
        for admin in standard_admins:
            add_org_admin(arg_apikey, org.id, admin['email'], admin['name'], admin['orgAccess'])

        chosen_org_admins = get_admin_list(arg_apikey, org.id)
        for new_admin in chosen_org_admins:
            if new_admin in standard_admins:
                print(f'{new_admin["name"]} added successfully.')
            else:
                print(f'{new_admin["name"]} not added successfully.')


if __name__ == '__main__':
    main(sys.argv[1:])
