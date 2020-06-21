'''
Push default RF profiles by network for one or more orgs:

2.4Ghz and 5Ghz 40Mhz Indoor Profile
5Ghz 40Mhz Indoor Profile

Or whatever you want that's in the dict newProfiles.

Yes, the profiles should be loaded in from a file, but this was a quicky job!
'''

import getopt
import json
import requests
import sys
import time
from copy import copy
from dataclasses import dataclass
from datetime import datetime
from getpass import getpass

# Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting
# dashboard API max request rate
API_EXEC_DELAY = 0.21

# connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 30
REQUESTS_READ_TIMEOUT = 30

# used by meraki_request_throttler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now()


@dataclass
class c_orgdata:
    '''Class for organization level data.'''

    id: str
    name: str
    menu: int
    shard: str


@dataclass
class c_netdata:
    '''Class for network level data.'''

    id: str
    type: str
    name: str
    tags: str
    menu: int
    orgId: str


@dataclass
class c_devicedata:
    '''Class for device level data.'''

    serial: str
    name: str
    mac: str
    networkId: str
    model: str
    notes: str
    dhcp: str
    lanIp: str


def print_user_text(p_message):
    '''Print a line of text meant for the user to read.

    Do not process these lines when chaining scripts
    '''
    print(f'@ {p_message}')


def print_help():
    '''Print help text.'''
    print_user_text('')
    print_user_text('meraki_request_throttler(), get_org_list(), filter_org_list()')
    print_user_text('method of getting opts, approach to Meraki API/requests')
    print_user_text('use are based off manageadmins.py at')
    print_user_text('https://github.com/meraki/automation-scripts/')
    print_user_text('by users mpapazog & shiyuechengineer, retrieved 10/19/2018')
    print_user_text('')
    print_user_text('To run the script, enter:')
    print_user_text('python getStaticVsDHCP.py -o <org> -f <file>')
    print_user_text('')
    print_user_text('-o can be a partial name in quotes with a single wildcard,')
    print_user_text('such as \'Calla*\' or \'*ssouri\'.')
    print_user_text('Use /all for all organizations you have access to.')
    print_user_text('')
    print_user_text('-f is the file the results will print to.')
    print_user_text('')
    print_user_text('Use double quotes (/"") in Windows to pass arguments')
    print_user_text('containing spaces. Names are case-sensitive.')
    print_user_text('')


def meraki_request_throttler(p_requestcount=1):
    '''Add delay to requests to avoid hitting shaper.'''
    global LAST_MERAKI_REQUEST

    if (datetime.now() - LAST_MERAKI_REQUEST).total_seconds() < \
            (API_EXEC_DELAY * p_requestcount):
        time.sleep(API_EXEC_DELAY * p_requestcount)

    LAST_MERAKI_REQUEST = datetime.now()
    return


def get_network_list(p_apikey, p_orgid, p_shardurl):
    '''Return list of networks for specified organization.'''
    meraki_request_throttler()
    r = ""
    try:
        r = requests.get(f'https://{p_shardurl}/api/v0/organizations/'
                         f'{p_orgid}/networks',
                         headers={'X-Cisco-Meraki-API-Key': p_apikey,
                                  'Content-Type': 'application/json'},
                         timeout=(REQUESTS_CONNECT_TIMEOUT,
                                  REQUESTS_READ_TIMEOUT))
    except:
        print_user_text('get_network_list: ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)

    rjson = r.json()

    return(rjson)


def get_org_list(p_apikey):
    '''Return the organizations' list for a specified admin.'''
    meraki_request_throttler()
    try:
        r = requests.get('https://api.meraki.com/api/v0/organizations',
                         headers={
                             'X-Cisco-Meraki-API-Key': p_apikey,
                             'Content-Type': 'application/json'},
                         timeout=(
                             REQUESTS_CONNECT_TIMEOUT,
                             REQUESTS_READ_TIMEOUT))
    except:
        print_user_text('ERROR 01: Unable to authenticate to Meraki cloud.')
        sys.exit(2)

    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id': 'null'})
        return returnvalue

    rjson = r.json()

    return(rjson)


def post_rf_profile(p_apikey, p_networkId, p_payload):
    '''Create new RF profile.'''
    url = f"https://api-mp.meraki.com/api/v0/networks/{p_networkId}/wireless/rfProfiles"
    headers = {
        'X-Cisco-Meraki-API-Key': p_apikey,
        'Content-Type': 'application/json'}

    json_payload = json.dumps(p_payload)
    try:
        r = requests.post(url,
                          headers=headers,
                          data=json_payload,
                          timeout=(REQUESTS_CONNECT_TIMEOUT,
                                   REQUESTS_READ_TIMEOUT))
    except Exception as error:
        print(error)
        print(r)
        sys.exit(2)

    if r.status_code == 400:
        print(f"{p_payload['name']} returned status code: {r.status_code}. Possible bad JSON or profile already exists.\n")
    elif r.status_code != 201:
        print(f"{p_payload['name']} returned status code: {r.status_code}\n")
    else:
        print(f"{p_payload['name']} added successfully.")

    return(r)


def get_rf_profiles(p_apikey, p_networkId):
    '''Pull all RF profiles for a network.'''

    url = f"https://api-mp.meraki.com/api/v0/networks/{p_networkId}/wireless/rfProfiles"
    meraki_request_throttler()
    try:
        r = requests.get(url,
                         headers={
                             'X-Cisco-Meraki-API-Key': p_apikey,
                             'Content-Type': 'application/json'},
                         timeout=(
                             REQUESTS_CONNECT_TIMEOUT,
                             REQUESTS_READ_TIMEOUT))
    except Exception as error:
        print_user_text(error)
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        return r.status_code

    rjson = r.json()

    return(rjson)


def profile_exist_check(p_existsList, p_newProfileName):
    '''Check if a profile with the same name exists.'''
    for extant in p_existsList:
        if extant['name'] == p_newProfileName:
            return extant
    return {}


def check_profile_settings_match(p_existingProfile, p_newProfile):
    '''Remove networkId and RF Profile ID then return true if existing matches new.'''
    # Assign to new var so you don't modify underlying dict
    modifiableProfile = copy(p_existingProfile)

    # New profiles don't include 'id' or 'networkId', so pop!
    remove = ['id', 'networkId']
    for item in remove:
        modifiableProfile.pop(item)

    # Check if all the values match. They should be in the same order.
    return modifiableProfile == p_newProfile


def filter_org_list(p_apikey, p_filter, p_orglist):
    '''
    Try to match a list of org IDs to a filter expression.

    Filter:
       /all    all organizations
       <name>  match if name matches. Name can contain one wildcard at start,
                 middle or end.
                 
    Based off code from https://github.com/meraki/automation-scripts/blob/master/manageadmins.py
    '''
    returnList = []

    flag_processall = False
    flag_gotwildcard = False
    if p_filter == '/all':
        flag_processall = True
    else:
        wildcardpos = p_filter.find('*')

        if wildcardpos > -1:
            flag_gotwildcard = True
            startsection = ''
            endsection = ''

            if wildcardpos == 0:
                # Wildcard at start of string, only got endsection.
                endsection = p_filter[1:]

            elif wildcardpos == len(p_filter) - 1:
                # Wildcard at start of string, only got startsection.
                startsection = p_filter[:-1]

            else:
                # Wildcard at middle of string, got both startsection and endsection.
                wildcardsplit = p_filter.split('*')
                startsection = wildcardsplit[0]
                endsection = wildcardsplit[1]

    # Add a number to make menu-making simpler
    menuNum = 1
    # Sort by org name
    sortOrgs = sorted(p_orglist, key=lambda p_orglist: p_orglist['name'])
    for org in sortOrgs:
        if flag_processall:
            returnList.append(c_orgdata(org['id'], org['name'], menuNum,
                              "api-mp.meraki.com"))
            menuNum += 1
        elif flag_gotwildcard:
            flag_gotmatch = True
            # Match startsection and endsection.
            startlen = len(startsection)
            endlen = len(endsection)

            if startlen > 0:
                if org['name'][:startlen] != startsection:
                    flag_gotmatch = False
            if endlen > 0:
                if org['name'][-endlen:] != endsection:
                    flag_gotmatch = False

            if flag_gotmatch:
                returnList.append(c_orgdata(org['id'], org['name'], menuNum,
                                  "api-mp.meraki.com"))
                menuNum += 1
        else:
            # Full name matches. Return one org.
            if org['name'] == p_filter:
                returnList.append(c_orgdata(org['id'], org['name'], menuNum,
                                  "api-mp.meraki.com"))

    return(returnList)


def main(argv):
    # Initialize variables for command line arguments
    arg_orgname = ''

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
                    arg_orgname = arg
    else:
        print("No opts given.")
        sys.exit()

    # Use getpass() to hide API key cuz you have manners
    arg_apikey = getpass("API key: ")

    # Dict of profiles, probably should be loaded in from a file really:
    # 2.4GHz + 5Ghz 40 MHz channel width
    # 2.4Ghz + 5Ghz 20 MHz channel width
    # 5Ghz 40 MHz channel width
    # 5Ghz 20 MHz channel width
    newProfiles = [{'name': '2.4Ghz and 5Ghz 40Mhz Indoor Profile', 'clientBalancingEnabled': True, 'minBitrateType': 'band', 'bandSelectionType': 'ap', 'apBandSettings': {'bandOperationMode': 'dual', 'bandSteeringEnabled': False}, 'twoFourGhzSettings': {'maxPower': 30, 'minPower': 5, 'minBitrate': 11, 'rxsop': None, 'validAutoChannels': [1, 6, 11], 'axEnabled': True}, 'fiveGhzSettings': {'maxPower': 30, 'minPower': 8, 'minBitrate': 12, 'rxsop': None, 'validAutoChannels': [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], 'channelWidth': '40'}}, {"name": "5Ghz 40Mhz Indoor Profile", "clientBalancingEnabled": True, "minBitrateType": "band", "bandSelectionType": "ap", "apBandSettings": {"bandOperationMode": "5Ghz", "bandSteeringEnabled": False}, "twoFourGhzSettings": {"maxPower": 30, "minPower": 5, "minBitrate": 11, "rxsop": None, "validAutoChannels": [], "axEnabled": True}, "fiveGhzSettings": {"maxPower": 30, "minPower": 8, "minBitrate": 12, "rxsop": None, "validAutoChannels": [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], "channelWidth": "40"}}, {"name": "5Ghz 20Mhz Indoor Profile", "clientBalancingEnabled": True, "minBitrateType": "band", "bandSelectionType": "ap", "apBandSettings": {"bandOperationMode": "5Ghz", "bandSteeringEnabled": False}, "twoFourGhzSettings": {"maxPower": 30, "minPower": 5, "minBitrate": 11, "rxsop": None, "validAutoChannels": [], "axEnabled": True}, "fiveGhzSettings": {"maxPower": 30, "minPower": 8, "minBitrate": 12, "rxsop": None, "validAutoChannels": [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], "channelWidth": "20"}}, {'name': '2.4Ghz and 5Ghz 20Mhz Indoor Profile', 'clientBalancingEnabled': True, 'minBitrateType': 'band', 'bandSelectionType': 'ap', 'apBandSettings': {'bandOperationMode': 'dual', 'bandSteeringEnabled': False}, 'twoFourGhzSettings': {'maxPower': 30, 'minPower': 5, 'minBitrate': 11, 'rxsop': None, 'validAutoChannels': [1, 6, 11], 'axEnabled': True}, 'fiveGhzSettings': {'maxPower': 30, 'minPower': 8, 'minBitrate': 12, 'rxsop': None, 'validAutoChannels': [36, 40, 44, 48, 52, 56, 60, 64, 100, 104, 108, 112, 136, 140, 144, 149, 153, 157, 161], 'channelWidth': '20'}}]

    # Get your orgs here
    raworglist = get_org_list(arg_apikey)
    if raworglist[0]['id'] == 'null':
        print_user_text('ERROR 08: Error retrieving organization list')
        sys.exit(2)

    # Match list of orgs to org filter
    matchedOrgs = filter_org_list(arg_apikey, arg_orgname, raworglist)

    # If no orgs matching - NK 2018-08-23
    if not matchedOrgs:
        print_user_text(f'Error 10: No organizations matching {arg_orgname}')
        sys.exit(2)

    # Push to network in org
    for org in matchedOrgs:
        networkList = get_network_list(arg_apikey, org.id, org.shard)
        # Put print lines like every other line and figure out why logic isn't triggering
        for network in networkList:
            if 'wireless' in network['productTypes']:
                print(f"{org.name}: {network['name']}")
                extantProfiles = get_rf_profiles(arg_apikey, network['id'])
                for profile in newProfiles:
                    currentProfile = profile_exist_check(extantProfiles, profile['name'])
                    if currentProfile:
                        if check_profile_settings_match(currentProfile, profile):
                            print(f"{profile['name']} already exists with CORRECT settings")
                        else:
                            print(f"{profile['name']} exists with WRONG settings.")
                    else:
                        post_rf_profile(arg_apikey, network['id'], profile)
                print("")
            else:
                print(f"{network['name']}: No wireless equipment.\n")


if __name__ == '__main__':
    main(sys.argv[1:])
