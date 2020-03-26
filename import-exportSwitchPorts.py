import sys, getopt, requests, json, time
from datetime import datetime

#Used for time.sleep(API_EXEC_DELAY). Delay added to avoid hitting dashboard API max request rate
API_EXEC_DELAY = 0.21

#connect and read timeouts for the Requests module
REQUESTS_CONNECT_TIMEOUT = 30
REQUESTS_READ_TIMEOUT    = 30

#used by merakirequestthrottler(). DO NOT MODIFY
LAST_MERAKI_REQUEST = datetime.now()

def printusertext(p_message):
    #prints a line of text that is meant for the user to read
    #do not process these lines when chaining scripts
    print('@ %s' % p_message)

def printhelp():
    #prints help text
    printusertext('')
    printusertext('merakirequestthrottler(), getorglist(), filterorglist(), method of getting')
    printusertext('opts, general approach to Meraki API/requests model use are based off')
    printusertext('manageadmins.py at')
    printusertext('https://github.com/meraki/automation-scripts/blob/master/manageadmins.py')
    printusertext('by users mpapazog and shiyuechengineer, retrieved 10/19/2018')
    printusertext('')
    printusertext('To run the script, enter:')
    printusertext('python import-exportSwitchPorts.py -k <api key> -s <serial number> -f <filename> -m <import or export>')
    printusertext('')
    printusertext('-m is mode. Import to update switchports from a file. Export to export switchports to file.')
    printusertext('-f is the filename the results will print to. Use double quotes around the file name.')
    printusertext('')
    printusertext('Use double quotes (/"") in Windows to pass arguments containing spaces. Names are case-sensitive.')
    printusertext('')

def merakirequestthrottler(p_requestcount=1):
    #makes sure there is enough time between API requests to Dashboard to avoid hitting shaper
    global LAST_MERAKI_REQUEST

    if (datetime.now()-LAST_MERAKI_REQUEST).total_seconds() < (API_EXEC_DELAY*p_requestcount):
        time.sleep(API_EXEC_DELAY*p_requestcount)

    LAST_MERAKI_REQUEST = datetime.now()
    return

# Put Switchports
def putSwitchport(p_apikey, p_serialnumber, p_switchport, p_switchnum, p_shardurl):
    merakirequestthrottler()
#    try:
    r = requests.put(f"https://{p_shardurl}/api/v0/devices/{p_serialnumber}/switchPorts/{p_switchnum}", data=json.dumps(p_switchport), headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    print(f"putSwitchport: {p_switchnum}")
    #except:
#        printusertext('Something broke')
#    print(r.status_code)
#        sys.exit(2)

    rjson = r.json()

    return(rjson)

# Get all switchports from a switch
def getSwitchports(p_apikey, p_serialnumber, p_shardurl):
    merakirequestthrottler()
    try:
        r = requests.get(f'https://{p_shardurl}/api/v0/devices/{p_serialnumber}/switchPorts', headers={'X-Cisco-Meraki-API-Key': p_apikey, 'Content-Type': 'application/json'},timeout=(REQUESTS_CONNECT_TIMEOUT, REQUESTS_READ_TIMEOUT))
    except:
        printusertext('ERROR 02: Unable to contact Meraki cloud')
        sys.exit(2)

    rjson = r.json()

    return(rjson)

def main(argv):
    #initialize variables for command line arguments
    arg_apikey  = ''
    arg_filename = ''
    arg_serial = ''
    arg_mode = ''

    #get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:s:f:m:')
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
        elif opt == '-s':
            # set to upper in case somebody manually types the SN
            arg_serial = arg.upper()
            if arg_serial == '':
                printusertext('No serial number. Copy it off the Meraki dash.')
                sys.exit()
        elif opt == '-f':
            arg_filename = arg
            if arg_filename == '':
                printusertext('No file name. Use a descriptive filename.')
                sys.exit()
        elif opt == "-m":
            # set to lowercase
            arg_mode = arg.lower()
            if arg_mode == '':
                printusertext('No mode given.')
                sys.exit()
            elif arg_mode != 'export':
                if arg_mode != 'import':
                    printusertext('Invalid mode given.')
                    sys.exit()

    # Using generic URL since it's just one device...
    shard = "api.meraki.com"

    # Check mode then do stuff
    if arg_mode == 'import':
        importFile = open(arg_filename, "r")
        if importFile.mode == 'r':
            switchportsList = json.loads(importFile.read())
            for port in switchportsList:
                # Update to be putSwitchport
                print(f"Updating {port['number']}")
                switchNum = port['number']
                empties = []
                for key, value in port.items():
                    if value == None:
                        empties.append(key)
                for item in empties:
                    try:
                        port.pop(item)
                    except:
                        print(f"Couldn't pop {item}")
                putSwitchport(arg_apikey, arg_serial, port, switchNum, shard)
                print(f"Put port: {port}")
            
        importFile.close()
    elif arg_mode == 'export':
        exportFile = open(arg_filename, "w+")
        if exportFile.mode == 'w+':
            switchportsList = json.dumps(getSwitchports(arg_apikey, arg_serial, shard))
            print("Writing switchports")
            exportFile.write(switchportsList)
            exportFile.close()
            print("Closing file. Please check.")

if __name__ == '__main__':
    main(sys.argv[1:])
