'''
Push default RF profiles by network for one or more orgs:

2.4Ghz and 5Ghz 40Mhz Indoor Profile
5Ghz 40Mhz Indoor Profile
2.4GHz and 5Ghz 20Mhz Indoor Profile
5GHz 20Mhz Indoor Profile

To run the script, enter:
python pushRfProfiles.py -o <org name>

-o can be a partial name in quotes such as 'Calla' or 'ssouri'.
Use /all for all organizations you have access to.
'''

import getopt
import json
import requests
import sys
from copy import copy
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

def get_network_list(api_key, org_id):
    '''
    Return list of networks for specified organization.
    
    :param api_key: Meraki Dashboard API key
    :param org_id: Organization ID number

    :return: List of dictionaries containing all networks for an organization.
    '''

    url = f'https://api-mp.meraki.com/api/v0/organizations/{org_id}/networks'
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    r = requests.request('GET', url, headers=headers)

    rjson = r.json()

    return(rjson)


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


def post_rf_profile(api_key, network_id, rf_profile_payload):
    '''
    Create new RF profile.
    
    :param api_key: Meraki Dashboard API key
    :param network_id: Network ID number
    :param rf_profile_payload: Dictionary containing RF profile settings

    :return: requests.Response object
    '''

    url = f"https://api-mp.meraki.com/api/v0/networks/{network_id}/wireless/rfProfiles"
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    json_payload = json.dumps(rf_profile_payload)
    r = requests.request('POST', url, headers=headers, data=json_payload)

    if r.status_code == 400:
        print(f"{rf_profile_payload['name']} returned status code: {r.status_code}. Possible bad JSON or profile already exists.\n")
    elif r.status_code != 201:
        print(f"{rf_profile_payload['name']} returned status code: {r.status_code}\n")
    else:
        print(f"{rf_profile_payload['name']} added successfully.")

    return(r)


def get_rf_profiles(api_key, network_id):
    '''
    Pull all RF profiles for a network.
    
    :param api_key: Meraki Dashboard API key
    :param network_id: Network ID number

    :return: List of dictionaries containing a network's configured RF Profiles
    '''

    url = f"https://api-mp.meraki.com/api/v0/networks/{network_id}/wireless/rfProfiles"
    headers = {'X-Cisco-Meraki-API-Key': api_key, 'Content-Type': 'application/json'}

    r = requests.request('GET', url, headers=headers)

    rjson = r.json()

    return(rjson)


def profile_exist_check(exists_list, new_profile_name):
    '''
    Check if a profile with the same name exists.
    
    :param exists_list: List of dictionaries containing a network's configured RF Profiles
    :param new_profile_name: Name of proposed new RF Profile

    :return: Empty dictionary if no matching name, or containing settings if match exists
    '''

    for extant in exists_list:
        if extant['name'] == new_profile_name:
            return extant
    return {}


def check_profile_settings_match(existing_profile, new_profile):
    '''
    Remove networkId and RF Profile ID then return true if existing matches new.
    
    :param existing_profile: Dictionary containing existing RF profile
    :param new_profile: Dictionary containing standard RF profile

    :return: bool

    '''
    # Copy to new var so you don't modify underlying dict
    modifiable_profile = copy(existing_profile)

    # New profiles don't include 'id' or 'networkId', so pop to remove.
    remove = ['id', 'networkId']
    for item in remove:
        modifiable_profile.pop(item)

    # Check if all the values match. They should be in the same order.
    return modifiable_profile == new_profile


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
    
    # 
    for org in sorted_orgs:
        if process_all:
            return_list.append(orgData(org['id'], org['name'], menu_num))
            menu_num += 1
        else:
            if (org['name'].lower()).find(filter) != -1:
                return_list.append(orgData(org['id'], org['name'], menu_num))
                menu_num += 1

    if len(return_list):
        return(return_list)
    else:
        print_user_text(f'ERROR: No organizations matching: {filter}')
        sys.exit(1)


def choose_org(org_list):
    '''
    Print a menu, then return user's chosen organization.
    
    :param org_list: List of dicts of Meraki organizations
    
    :return: List of dicts containing matching org.
    '''

    attempts = 0

    while (attempts < 3):
        attempts += 1
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
            # If no org matches, print notice then quit.
            print(f'No matching menu item {chosen_org}\n')

    print("No valid choice made. Exiting...")
    sys.exit()


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

    # Embedded profiles in script because original audience was not comfortable
    # modifying a CSV to update these, or remembering to download the CSV from source.

    # Dict of profiles:
    # 2.4GHz + 5Ghz 40 MHz channel width
    # 2.4Ghz + 5Ghz 20 MHz channel width
    # 5Ghz 40 MHz channel width
    # 5Ghz 20 MHz channel width
    newProfiles = [{'name': '2.4Ghz and 5Ghz 40Mhz Indoor Profile', 'clientBalancingEnabled': True, 'minBitrateType': 'band', 'bandSelectionType': 'ap', 'apBandSettings': {'bandOperationMode': 'dual', 'bandSteeringEnabled': False}, 'twoFourGhzSettings': {'maxPower': 30, 'minPower': 5, 'minBitrate': 11, 'rxsop': None, 'validAutoChannels': [1, 6, 11], 'axEnabled': True}, 'fiveGhzSettings': {'maxPower': 30, 'minPower': 8, 'minBitrate': 12, 'rxsop': None, 'validAutoChannels': [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], 'channelWidth': '40'}}, {"name": "5Ghz 40Mhz Indoor Profile", "clientBalancingEnabled": True, "minBitrateType": "band", "bandSelectionType": "ap", "apBandSettings": {"bandOperationMode": "5Ghz", "bandSteeringEnabled": False}, "twoFourGhzSettings": {"maxPower": 30, "minPower": 5, "minBitrate": 11, "rxsop": None, "validAutoChannels": [], "axEnabled": True}, "fiveGhzSettings": {"maxPower": 30, "minPower": 8, "minBitrate": 12, "rxsop": None, "validAutoChannels": [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], "channelWidth": "40"}}, {"name": "5Ghz 20Mhz Indoor Profile", "clientBalancingEnabled": True, "minBitrateType": "band", "bandSelectionType": "ap", "apBandSettings": {"bandOperationMode": "5Ghz", "bandSteeringEnabled": False}, "twoFourGhzSettings": {"maxPower": 30, "minPower": 5, "minBitrate": 11, "rxsop": None, "validAutoChannels": [], "axEnabled": True}, "fiveGhzSettings": {"maxPower": 30, "minPower": 8, "minBitrate": 12, "rxsop": None, "validAutoChannels": [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], "channelWidth": "20"}}, {'name': '2.4Ghz and 5Ghz 20Mhz Indoor Profile', 'clientBalancingEnabled': True, 'minBitrateType': 'band', 'bandSelectionType': 'ap', 'apBandSettings': {'bandOperationMode': 'dual', 'bandSteeringEnabled': False}, 'twoFourGhzSettings': {'maxPower': 30, 'minPower': 5, 'minBitrate': 11, 'rxsop': None, 'validAutoChannels': [1, 6, 11], 'axEnabled': True}, 'fiveGhzSettings': {'maxPower': 30, 'minPower': 8, 'minBitrate': 12, 'rxsop': None, 'validAutoChannels': [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], 'channelWidth': '20'}}]

    # Get your organization list and check if your API key works.
    raw_org_list = get_org_list(arg_api_key)

    # Match list of orgs to org filter
    filtered_orgs = filter_org_list(arg_api_key, arg_org_name, raw_org_list)

    if len(filtered_orgs) >= 0:
        matched_orgs = choose_org(filtered_orgs)
    else:
        print("\nRunning against all orgs...")
        matched_orgs = filtered_orgs
        print(matched_orgs)
    
    # Push to network in org
    for org in matched_orgs:
        network_list = get_network_list(arg_api_key, org.id)
        # Put print lines like every other line and figure out why logic isn't triggering
        for network in network_list:

            # Can only add RF profiles to networks with actual APs.
            if 'wireless' in network['productTypes']:
                print(f"\n{org.name}: {network['name']}")
                extantProfiles = get_rf_profiles(arg_api_key, network['id'])

                for profile in newProfiles:
                    # Check if profile by that name already exists.
                    profile_exists = profile_exist_check(extantProfiles, profile['name'])
                    if profile_exists:
                        if check_profile_settings_match(profile_exists, profile):
                            print(f"{profile['name']} already exists with CORRECT settings")
                        else:
                            print(f"{profile['name']} exists with WRONG settings.")
                    else:
                        post_rf_profile(arg_api_key, network['id'], profile)
                print("")

            else:
                # If no wireless APs in network, print notice and move on.
                print(f"{network['name']}: No wireless equipment.\n")


if __name__ == '__main__':
    main(sys.argv[1:])
