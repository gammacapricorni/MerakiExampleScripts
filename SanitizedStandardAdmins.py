import sys, getopt, requests, json, time, pprint
from dataclasses import dataclass
from datetime import datetime
from re import compile

#Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 30
REQUESTS_READ_TIMEOUT    = 30

#used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now()

LINE_SEPARATOR = '-' * 20

@dataclass
class c_orgdata:
    id: str
    name: str
    menu: int
    shard: str

def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message)

def printhelp():
    #prints help text
    printusertext('')
    printusertext('Use to update pre-existing Meraki Org with the standard set of admins')
    printusertext('')
    printusertext('merakirequestthrottler(), getorglist(), filterorglist(), method of getting')
    printusertext('opts, general approach to Meraki API/requests model use are based off')
    printusertext('manageadmins.py at')
    printusertext('https://github.com/meraki/automation-scripts/blob/master/manageadmins.py')
    printusertext('by users mpapazog and shiyuechengineer, retrieved 10/19/2018 by Nash King')
    printusertext('')
    printusertext('To run the script, enter:')
    printusertext('python standardAdmins.py -k <api key> -o <org>')
    printusertext('')
    printusertext('-o can be a partial name in quotes with a single wildcard, such as "Calla*"')
    printusertext('')
    printusertext('Use double quotes (\"\") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    printusertext('')

def merakirequestthrottler(p_requestcount=1):
    #makes sure there is enough time between API requests to Dashboard to avoid hitting shaper
    global LAST_MERAKI_REQUEST

    if (datetime.now()-LAST_MERAKI_REQUEST).total_seconds() < (API_EXEC_DELAY*p_requestcount):
        time.sleep(API_EXEC_DELAY*p_requestcount)

    LAST_MERAKI_REQUEST = datetime.now()
    return

# Get shard
def getshardurl(p_apikey, p_orgid):
	#Looks up shard URL for a specific org. Use this URL instead of 'dashboard.meraki.com'
	# when making API calls with API accounts that can access multiple orgs.
	#On failure returns 'null'

	r = requests.get('https://dashboard.meraki.com/api/v0/organizations/%s/snmp' % p_orgid, headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'})

	if r.status_code != requests.codes.ok:
		return 'null'

	rjson = r.json()

	return(rjson['hostname'])

# Get org name etc for one organization
def getorginfo(p_apikey, p_orgid, p_shardurl):
    merakirequestthrottler()
    try:
        r = requests.get(f"https://{p_shardurl}/api/v0/organizations/{p_orgid}", headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        printusertext('ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)

    rjson = r.json()

    return(rjson)

def getorglist(p_apikey):
    #returns the organizations' list for a specified admin

    merakirequestthrottler()
    try:
        r = requests.get('https://api.meraki.com/api/v0/organizations', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        printusertext('ERROR 01: Unable to contact Meraki cloud')
        sys.exit(2)

    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id':'null'})
        return returnvalue

    rjson = r.json()

    return(rjson)

def getAdminList(p_apikey, p_orgid, p_shardurl):
    #returns the organizations' list for a specified admin

    merakirequestthrottler()
    try:
        r = requests.get(f'https://{p_shardurl}/api/v0/organizations/{p_orgid}/admins', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        printusertext('ERROR 01: Unable to contact Meraki cloud')
        sys.exit(2)

    returnvalue = []
    if r.status_code != requests.codes.ok:
        returnvalue.append({'id':'null'})
        return returnvalue

    rjson = r.json()

    return(rjson)

# Print menu of possible matching organizations
def printOrgMenu(p_orglist):
    print("Called printOrgMenu")
    menuchoice = ''
    quitOpt = compile("^[q|Q]")
    numbers = compile("^[0-9]")
    allOpt = compile("^[aA]")

    print('\nChoose organization from list, or Q to Quit')
    # Loop til menuchoice is a valid response or a valid org is chosen
    while menuchoice == '':
        for org in p_orglist:
            #Print each org
            print(f'{org.menu}: {org.name}')
        print('Q: Quit program')
        print('Enter choice: ', end='')
        menuchoice = input()
        print('')
        # Check if menuchoice is Q or q
        if quitOpt.match(menuchoice):
            sys.exit()
        # Check if menuchoice is numbers
        elif menuchoice is not '':
            for org in p_orglist:
                # If org.menu matches, then return org
                if org.menu == int(menuchoice):
                    return(org)
            # If nothing matches, set menuchoice to keep looping
            print('Invalid choice. Please try again.')
            menuchoice = ''
        else:
            print('Invalid choice. Please try again.')
            menuchoice = ''

def addorgadmin(p_apikey, p_orgid, p_shardurl, p_email, p_name, p_privilege):
   #creates admin into an organization

    merakirequestthrottler()

    try:
        r = requests.post('https://%s/api/v0/organizations/%s/admins' % (p_shardurl, p_orgid), data=json.dumps({'name': p_name, 'email': p_email, 'orgAccess': p_privilege}), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'}, timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        printusertext('ERROR 03: Unable to contact Meraki cloud')
        sys.exit(2)

    if r.status_code != requests.codes.ok:
        if r.status_code == 400:
            printusertext('WARNING: Email already registered with a Cisco Meraki Dashboard account. For security purposes, that user must verify their email address before administrator permissions can be granted here.')
        return ('fail')
    else:
        print(f"Added {admin.email}")

    return('ok')

def filterOrgList(p_apikey, p_filter, p_orglist):
    #tried to match a list of org IDs to a filter expression
    #   /all    all organizations
    #   <name>  match if name matches. name can contain one wildcard at start, middle or end

    returnlist = []

    flag_processall     = False
    flag_gotwildcard    = False
    if p_filter == '/all':
        flag_processall = False
        print("No /all allowed on admin adds.")
    else:
        wildcardpos = p_filter.find('*')

        if wildcardpos > -1:
            flag_gotwildcard = True
            startsection    = ''
            endsection      = ''

            if   wildcardpos == 0:
                #wildcard at start of string, only got endsection
                endsection   = p_filter[1:]

            elif wildcardpos == len(p_filter) - 1:
                #wildcard at start of string, only got startsection
                startsection = p_filter[:-1]
            else:
                #wildcard at middle of string, got both startsection and endsection
                wildcardsplit = p_filter.split('*')
                startsection  = wildcardsplit[0]
                endsection    = wildcardsplit[1]

    for org in p_orglist:
        if flag_processall:
            returnlist.append(c_orgdata(org['id'], org['name'], '', getshardurl(p_apikey, org['id'])))
        elif flag_gotwildcard:
            flag_gotmatch = True
            #match startsection and endsection
            startlen = len(startsection)
            endlen   = len(endsection)

            if startlen > 0:
                if org['name'][:startlen] != startsection:
                    flag_gotmatch = False
            if endlen   > 0:
                if org['name'][-endlen:]   != endsection:
                    flag_gotmatch = False

            if flag_gotmatch:
                returnlist.append(c_orgdata(org['id'], org['name'], '', getshardurl(p_apikey, org['id'])))

        else:
            #match full name
            if org['name'] == p_filter:
                returnlist.append(c_orgdata(org['id'], org['name'], '', getshardurl(p_apikey, org['id'])))
    sortorgs = []
    sortorgs = sorted(returnlist, key=lambda c_orgdata: c_orgdata.name)
    menunum = 1
    for org in sortorgs:
        org.menu = menunum
        menunum += 1
    return(sortorgs)

def main(argv):
    #initialize variables for command line arguments
    arg_apikey  = ''
    arg_orgname = ''

    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:')
    except getopt.GetoptError:
        printusertext('Error getting opts.')
        sys.exit(2)

    for opt, arg in opts:
        if   opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            arg_apikey  = arg
            if arg_apikey == '':
                printusertext('No API key')
                sys.exit()
        elif opt == '-o':
            arg_orgname = arg
            if arg_orgname == '':
                printusertext('No org name')
                sys.exit()

    #get list org all orgs belonging to this admin
    raworglist = getorglist(arg_apikey)
    if raworglist[0]['id'] == 'null':
        printusertext('ERROR 08: Error retrieving organization list')
        sys.exit(2)

    #match list of orgs to org filter
    matchedorgs = filterOrgList(arg_apikey, arg_orgname, raworglist)

    #if no orgs matching - NK 2018-08-23
    if not matchedorgs:
        printusertext(f'Error 10: No organizations matching {arg_orgname}')
        sys.exit(2)

    # Print menu of possible matches
    printOrgMenu(matchedorgs)

    # Org ID for the standard organization
    standardMSPOrg = "REPLACE WITH YOUR ORG ID"
    # Get admin list from standard org
    standardAdmins = getAdminList(arg_apikey, standardMSPOrg, getshardurl(arg_apikey, standardMSPOrg))

    # For each org that matched
    for org in matchedorgs:
        # Add each admin from the standard organization
        for admin in standardAdmins:
            addorgadmin(arg_apikey, org.id, org.shard, admin['email'], admin['name'], admin['orgAccess'])

if __name__ == '__main__':
    main(sys.argv[1:])
