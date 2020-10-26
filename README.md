# MerakiExampleScripts

Assorted scripts using the Meraki dashboard API. Primarily posted for sharing on the Meraki Community Forum.

### AddStandardAdmins: 
Using an example organization's org ID, copy its org-level admins to another org.

### add_standard_rf_profiles:
Add standardized RF profiles to either one or all organizations. Extremely helpful if you're managing a large number of wireless networks for any reason. If a profile with a matching name exists, the script will check to see if the settings and tell you if the existing profile has the correct settings.

### import-exportSwitchPorts.py
Import switch port config from or export switchport configs to a file, as JSON. Useful when copying switchport configs between switches on separate networks.
