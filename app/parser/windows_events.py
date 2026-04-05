# app/parser/windows_events.py
# Windows Event ID lookup table and structured log parser.

from typing import Dict, Any, Optional, List

# Event ID lookup table.
# Format: event_id -> (severity, section, explanation, threat)
EVENT_ID_MAP: Dict[int, tuple] = {
    # -------------------------------------------------------
    # ACCOUNT LOGON
    # -------------------------------------------------------
    4624: ("low",      "Auth",        "Successful logon.", "Auth"),
    4625: ("high",     "Security",    "Login failed. Wrong credentials or account does not exist.", "Auth"),
    4626: ("low",      "Auth",        "User/device claims information logged for a new logon.", "Auth"),
    4627: ("low",      "Auth",        "Group membership information logged for a new logon.", "Auth"),
    4634: ("low",      "Auth",        "User logged off.", "Auth"),
    4647: ("low",      "Auth",        "User initiated logoff.", "Auth"),
    4648: ("high",     "Security",    "Login attempted with explicit credentials while already logged in. Possible pass-the-hash.", "Auth"),
    4649: ("high",     "Security",    "A replay attack was detected.", "Auth"),
    4675: ("moderate", "Auth",        "SIDs were filtered during logon.", "Auth"),
    4769: ("low",      "Auth",        "A Kerberos service ticket was requested.", "Auth"),
    4770: ("low",      "Auth",        "A Kerberos service ticket was renewed.", "Auth"),
    4771: ("moderate", "Auth",        "Kerberos pre-authentication failed.", "Auth"),
    4772: ("moderate", "Auth",        "A Kerberos authentication ticket request failed.", "Auth"),
    4773: ("moderate", "Auth",        "A Kerberos service ticket request failed.", "Auth"),
    4774: ("low",      "Auth",        "An account was mapped for logon.", "Auth"),
    4775: ("moderate", "Auth",        "An account could not be mapped for logon.", "Auth"),
    4776: ("moderate", "Auth",        "The domain controller validated credentials for an account.", "Auth"),
    4777: ("high",     "Auth",        "The domain controller failed to validate credentials.", "Auth"),
    4778: ("low",      "Auth",        "A session was reconnected to a window station.", "Auth"),
    4779: ("low",      "Auth",        "A session was disconnected from a window station.", "Auth"),
    4800: ("low",      "Auth",        "The workstation was locked.", "Auth"),
    4801: ("low",      "Auth",        "The workstation was unlocked.", "Auth"),
    4802: ("low",      "Auth",        "The screen saver was invoked.", "Auth"),
    4803: ("low",      "Auth",        "The screen saver was dismissed.", "Auth"),
    4964: ("high",     "Auth",        "Special groups were assigned to a new logon.", "Auth"),
    # -------------------------------------------------------
    # ACCOUNT MANAGEMENT
    # -------------------------------------------------------
    4720: ("high",     "Security",    "A user account was created.", "AccountChange"),
    4722: ("moderate", "Security",    "A user account was enabled.", "AccountChange"),
    4723: ("moderate", "Security",    "A user attempted to change an account password.", "AccountChange"),
    4724: ("moderate", "Security",    "An administrator attempted to reset a password.", "AccountChange"),
    4725: ("high",     "Security",    "A user account was disabled.", "AccountChange"),
    4726: ("high",     "Security",    "A user account was deleted.", "AccountChange"),
    4727: ("high",     "Privilege",   "A security-enabled global group was created.", "Privilege"),
    4728: ("high",     "Privilege",   "A member was added to a security-enabled global group.", "Privilege"),
    4729: ("moderate", "Privilege",   "A member was removed from a security-enabled global group.", "Privilege"),
    4730: ("high",     "Privilege",   "A security-enabled global group was deleted.", "Privilege"),
    4731: ("high",     "Privilege",   "A security-enabled local group was created.", "Privilege"),
    4732: ("high",     "Privilege",   "A user was added to a privileged local group.", "Privilege"),
    4733: ("moderate", "Privilege",   "A member was removed from a security-enabled local group.", "Privilege"),
    4734: ("high",     "Privilege",   "A security-enabled local group was deleted.", "Privilege"),
    4735: ("high",     "Privilege",   "A security-enabled local group was changed.", "Privilege"),
    4737: ("high",     "Privilege",   "A security-enabled global group was changed.", "Privilege"),
    4738: ("moderate", "AccountChange","A user account was changed.", "AccountChange"),
    4739: ("high",     "Security",    "Domain policy was changed.", "Tampering"),
    4740: ("moderate", "Auth",        "Account locked out after too many failed login attempts.", "Auth"),
    4741: ("high",     "Security",    "A computer account was created.", "AccountChange"),
    4742: ("moderate", "Security",    "A computer account was changed.", "AccountChange"),
    4743: ("high",     "Security",    "A computer account was deleted.", "AccountChange"),
    4744: ("high",     "Privilege",   "A security-disabled local group was created.", "Privilege"),
    4748: ("high",     "Privilege",   "A security-disabled local group was deleted.", "Privilege"),
    4749: ("high",     "Privilege",   "A security-disabled global group was created.", "Privilege"),
    4750: ("moderate", "Privilege",   "A security-disabled global group was changed.", "Privilege"),
    4753: ("high",     "Privilege",   "A security-disabled global group was deleted.", "Privilege"),
    4754: ("high",     "Privilege",   "A security-enabled universal group was created.", "Privilege"),
    4755: ("high",     "Privilege",   "A security-enabled universal group was changed.", "Privilege"),
    4756: ("high",     "Privilege",   "A user was added to a security group.", "Privilege"),
    4757: ("moderate", "Privilege",   "A member was removed from a security-enabled universal group.", "Privilege"),
    4758: ("high",     "Privilege",   "A security-enabled universal group was deleted.", "Privilege"),
    4764: ("high",     "Privilege",   "A group type was changed.", "Privilege"),
    4765: ("high",     "Privilege",   "SID History was added to an account.", "Privilege"),
    4766: ("high",     "Privilege",   "An attempt to add SID History to an account failed.", "Privilege"),
    4767: ("moderate", "Auth",        "A user account was unlocked.", "Auth"),
    4780: ("high",     "Security",    "The ACL was set on accounts that are members of administrators groups.", "Privilege"),
    4781: ("moderate", "AccountChange","The name of an account was changed.", "AccountChange"),
    4782: ("high",     "Security",    "The password hash of an account was accessed.", "Auth"),
    4793: ("moderate", "Security",    "The Password Policy Checking API was called.", "Security"),
    4794: ("high",     "Security",    "An attempt was made to set the DSRM administrator password.", "Security"),
    4798: ("moderate", "Security",    "A user's local group membership was enumerated.", "Security"),
    4799: ("moderate", "Security",    "A security-enabled local group membership was enumerated.", "Security"),
    # -------------------------------------------------------
    # POLICY CHANGE
    # -------------------------------------------------------
    4670: ("moderate", "Security",    "Permissions on an object were changed.", "Security"),
    4703: ("moderate", "Security",    "A user right was adjusted.", "Privilege"),
    4704: ("moderate", "Security",    "A user right was assigned.", "Privilege"),
    4705: ("moderate", "Security",    "A user right was removed.", "Privilege"),
    4706: ("high",     "Security",    "A new trust was created to a domain.", "Security"),
    4707: ("high",     "Security",    "A trust to a domain was removed.", "Security"),
    4709: ("moderate", "Security",    "IPsec Services was started.", "Network"),
    4710: ("moderate", "Security",    "IPsec Services was disabled.", "Network"),
    4711: ("moderate", "Security",    "IPsec policy was changed.", "Network"),
    4713: ("high",     "Security",    "Kerberos policy was changed.", "Security"),
    4714: ("moderate", "Security",    "Encrypted data recovery policy was changed.", "Security"),
    4715: ("high",     "Security",    "The audit policy on an object was changed.", "Tampering"),
    4716: ("high",     "Security",    "Trusted domain information was modified.", "Security"),
    4717: ("moderate", "Security",    "System security access was granted to an account.", "Security"),
    4718: ("moderate", "Security",    "System security access was removed from an account.", "Security"),
    4719: ("high",     "Tampering",   "System audit policy was changed. Someone may be disabling security logging.", "Tampering"),
    4864: ("moderate", "Security",    "A namespace collision was detected.", "Security"),
    4865: ("moderate", "Security",    "A trusted forest information entry was added.", "Security"),
    4866: ("moderate", "Security",    "A trusted forest information entry was removed.", "Security"),
    4867: ("moderate", "Security",    "A trusted forest information entry was modified.", "Security"),
    4904: ("high",     "Tampering",   "An attempt was made to register a security event source.", "Tampering"),
    4905: ("high",     "Tampering",   "An attempt was made to unregister a security event source.", "Tampering"),
    4906: ("high",     "Tampering",   "The CrashOnAuditFail value has changed.", "Tampering"),
    4907: ("moderate", "Security",    "Auditing settings on an object were changed.", "Security"),
    4908: ("moderate", "Security",    "Special Groups Logon table was modified.", "Security"),
    4912: ("high",     "Tampering",   "Per-user audit policy was changed.", "Tampering"),
    4944: ("moderate", "Network",     "The following policy was active when the Windows Firewall started.", "Network"),
    4945: ("moderate", "Network",     "A rule was listed when the Windows Firewall started.", "Network"),
    4946: ("moderate", "Network",     "A rule was added to the Windows Firewall exception list.", "Network"),
    4947: ("moderate", "Network",     "A rule was modified in the Windows Firewall exception list.", "Network"),
    4948: ("moderate", "Network",     "A rule was deleted from the Windows Firewall exception list.", "Network"),
    4949: ("moderate", "Network",     "Windows Firewall settings were restored to the default values.", "Network"),
    4950: ("moderate", "Network",     "A Windows Firewall setting was changed.", "Network"),
    4951: ("moderate", "Network",     "A rule was ignored because its major version number was not recognized.", "Network"),
    4952: ("moderate", "Network",     "Parts of a rule were ignored because its minor version number was not recognized.", "Network"),
    4953: ("moderate", "Network",     "Windows Firewall ignored a rule because it could not be parsed.", "Network"),
    4954: ("high",     "Network",     "Windows Firewall group policy settings changed.", "Network"),
    4956: ("moderate", "Network",     "Windows Firewall has changed the active profile.", "Network"),
    4957: ("moderate", "Network",     "Windows Firewall did not apply a rule.", "Network"),
    4958: ("moderate", "Network",     "Windows Firewall did not apply a rule because the rule referred to items not configured on this computer.", "Network"),
    # -------------------------------------------------------
    # PRIVILEGE USE
    # -------------------------------------------------------
    4672: ("high",     "Security",    "Admin privileges assigned at login.", "Privilege"),
    4673: ("moderate", "Privilege",   "A privileged service was called.", "Privilege"),
    4674: ("moderate", "Privilege",   "An operation was attempted on a privileged object.", "Privilege"),
    4985: ("moderate", "Security",    "The state of a transaction has changed.", "Security"),
    # -------------------------------------------------------
    # OBJECT ACCESS
    # -------------------------------------------------------
    4656: ("moderate", "FileSystem",  "A handle to an object was requested.", "FileSystem"),
    4657: ("moderate", "Persistence", "A registry value was modified.", "Persistence"),
    4658: ("low",      "FileSystem",  "A handle to an object was closed.", "FileSystem"),
    4659: ("moderate", "FileSystem",  "A handle to an object was requested with intent to delete.", "FileSystem"),
    4660: ("moderate", "FileSystem",  "An object was deleted.", "FileSystem"),
    4661: ("moderate", "FileSystem",  "A handle to an object was requested.", "FileSystem"),
    4662: ("moderate", "Security",    "An operation was performed on an object.", "Security"),
    4663: ("moderate", "FileSystem",  "An attempt was made to access an object.", "FileSystem"),
    4664: ("moderate", "FileSystem",  "An attempt was made to create a hard link.", "FileSystem"),
    4665: ("moderate", "Security",    "An attempt was made to create an application client context.", "Security"),
    4666: ("moderate", "Security",    "An application attempted an operation.", "Security"),
    4667: ("moderate", "Security",    "An application client context was deleted.", "Security"),
    4668: ("moderate", "Security",    "An application was initialized.", "Security"),
    4671: ("moderate", "Security",    "An application attempted to access a blocked ordinal through the TBS.", "Security"),
    5140: ("moderate", "Network",     "A network share object was accessed.", "Network"),
    5141: ("high",     "Network",     "A network share object was deleted.", "Network"),
    5142: ("moderate", "Network",     "A network share object was added.", "Network"),
    5143: ("moderate", "Network",     "A network share object was modified.", "Network"),
    5144: ("high",     "Network",     "A network share object was deleted.", "Network"),
    5145: ("moderate", "Network",     "A network share object was checked for access.", "Network"),
    5168: ("moderate", "Network",     "SPN check for SMB/SMB2 failed.", "Network"),
    4698: ("high",     "Security",    "A scheduled task was created. Check if this is expected.", "Persistence"),
    4699: ("high",     "Security",    "A scheduled task was deleted.", "Persistence"),
    4700: ("high",     "Security",    "A scheduled task was enabled.", "Persistence"),
    4701: ("high",     "Security",    "A scheduled task was disabled.", "Persistence"),
    4702: ("moderate", "Security",    "A scheduled task was updated.", "Persistence"),
    # -------------------------------------------------------
    # SYSTEM EVENTS
    # -------------------------------------------------------
    4608: ("low",      "System",      "Windows is starting up.", "System"),
    4609: ("low",      "System",      "Windows is shutting down.", "System"),
    4610: ("low",      "System",      "An authentication package has been loaded by the Local Security Authority.", "System"),
    4611: ("moderate", "System",      "A trusted logon process has been registered with the Local Security Authority.", "System"),
    4612: ("moderate", "System",      "Internal resources allocated for the queuing of audit messages have been exhausted, leading to the loss of some audits.", "Tampering"),
    4614: ("moderate", "System",      "A notification package has been loaded by the Security Account Manager.", "System"),
    4615: ("high",     "System",      "Invalid use of LPC port.", "System"),
    4616: ("moderate", "System",      "System time was changed.", "Tampering"),
    4618: ("high",     "Tampering",   "A monitored security event pattern has occurred.", "Tampering"),
    4621: ("high",     "System",      "Administrator recovered system from CrashOnAuditFail.", "System"),
    4622: ("moderate", "System",      "A security package has been loaded by the Local Security Authority.", "System"),
    4697: ("high",     "Persistence", "A service was installed on the system. Review if this service is expected.", "Persistence"),
    # -------------------------------------------------------
    # SECURITY LOG
    # -------------------------------------------------------
    1100: ("high",     "Tampering",   "The event logging service has shut down.", "Tampering"),
    1101: ("high",     "Tampering",   "Audit events have been dropped by the transport.", "Tampering"),
    1102: ("high",     "Security",    "Audit log was cleared. Someone may be covering tracks.", "Tampering"),
    1104: ("high",     "Tampering",   "The security log is now full.", "Tampering"),
    1105: ("moderate", "System",      "Event log automatic backup.", "System"),
    1108: ("moderate", "System",      "The event logging service encountered an error.", "System"),
    # -------------------------------------------------------
    # PROCESS CREATION / TAMPERING
    # -------------------------------------------------------
    4688: ("high",     "Security",    "A new process was created.", "Execution"),
    4689: ("low",      "Execution",   "A process has exited.", "Execution"),
    4690: ("moderate", "Security",    "An attempt was made to duplicate a handle to an object.", "Security"),
    4691: ("moderate", "Security",    "Indirect access to an object was requested.", "Security"),
    4696: ("moderate", "Security",    "A primary token was assigned to process.", "Security"),
    # -------------------------------------------------------
    # SECURITY INTEGRITY
    # -------------------------------------------------------
    5038: ("high",     "Security",    "Code integrity check failed. A system file may have been modified.", "Tampering"),
    5056: ("moderate", "Security",    "A cryptographic self-test was performed.", "Security"),
    5057: ("high",     "Security",    "A cryptographic primitive operation failed.", "Security"),
    5058: ("moderate", "Security",    "Key file operation.", "Security"),
    5059: ("moderate", "Security",    "Key migration operation.", "Security"),
    5060: ("high",     "Security",    "Verification operation failed.", "Security"),
    5061: ("moderate", "Security",    "Cryptographic operation.", "Security"),
    5062: ("moderate", "Security",    "A kernel-mode cryptographic self-test was performed.", "Security"),
    # -------------------------------------------------------
    # NETWORK POLICY SERVER / FILTERING PLATFORM
    # -------------------------------------------------------
    4820: ("high",     "Auth",        "A Kerberos TGT was denied because the device does not meet access control restrictions.", "Auth"),
    4821: ("high",     "Auth",        "A Kerberos service ticket was denied because the user does not meet access control restrictions.", "Auth"),
    4822: ("high",     "Auth",        "NTLM authentication failed because the account is a member of the Protected User group.", "Auth"),
    4823: ("high",     "Auth",        "NTLM authentication failed because access control restrictions are required.", "Auth"),
    4824: ("high",     "Auth",        "Kerberos pre-authentication failed using DES or RC4.", "Auth"),
    5031: ("moderate", "Network",     "Windows Firewall blocked an application from accepting incoming connections.", "Network"),
    5148: ("high",     "Network",     "The Windows Filtering Platform has detected a DoS attack and entered a defensive mode.", "Network"),
    5149: ("moderate", "Network",     "The DoS attack has subsided and normal processing is being resumed.", "Network"),
    5150: ("high",     "Network",     "The Windows Filtering Platform blocked a packet.", "Network"),
    5151: ("high",     "Network",     "A more restrictive Windows Filtering Platform filter blocked a packet.", "Network"),
    5152: ("high",     "Security",    "Windows Firewall blocked a packet.", "Network"),
    5153: ("moderate", "Network",     "A more restrictive Windows Filtering Platform filter blocked a packet.", "Network"),
    5154: ("low",      "Network",     "Windows Filtering Platform permitted an application or service to listen on a port.", "Network"),
    5155: ("moderate", "Network",     "Windows Filtering Platform blocked an application or service from listening on a port.", "Network"),
    5156: ("low",      "Network",     "Windows Filtering Platform permitted a connection.", "Network"),
    5157: ("moderate", "Network",     "Windows Filtering Platform blocked a connection.", "Network"),
    5158: ("low",      "Network",     "Windows Filtering Platform permitted a bind to a local port.", "Network"),
    5159: ("moderate", "Network",     "Windows Filtering Platform blocked a bind to a local port.", "Network"),
    # -------------------------------------------------------
    # ACTIVE DIRECTORY / KERBEROS
    # -------------------------------------------------------
    4768: ("low",      "Auth",        "A Kerberos authentication ticket was requested.", "Auth"),
    4786: ("moderate", "Security",    "The certificate for a certification authority was changed.", "Security"),
    4787: ("moderate", "Security",    "The off-line signing of a certification authority was completed.", "Security"),
    4788: ("moderate", "Security",    "The member in a Cross Forest was removed.", "Security"),
    4789: ("moderate", "Security",    "The member in a Cross Forest was added.", "Security"),
    4790: ("moderate", "Security",    "A cross-forest trust entry for member was created.", "Security"),
    4791: ("moderate", "Security",    "A basic application group was changed.", "Security"),
    4792: ("high",     "Security",    "A basic application group was deleted.", "Security"),
    # -------------------------------------------------------
    # REMOVABLE STORAGE / BITLOCKER
    # -------------------------------------------------------
    4816: ("moderate", "Security",    "RPC detected an integrity violation while decrypting an incoming message.", "Security"),
    6400: ("high",     "Security",    "BitLocker Drive Encryption failed to set up a backup of the recovery information.", "Security"),
    6401: ("moderate", "Security",    "BitLocker Drive Encryption started recovery mode.", "Security"),
    6402: ("moderate", "Security",    "BitLocker Drive Encryption started recovery.", "Security"),
    6403: ("moderate", "Security",    "BitLocker Drive Encryption failed to recover.", "Security"),
    6404: ("high",     "Security",    "BitLocker Drive Encryption detected an attempt to unlock a drive.", "Security"),
    6405: ("moderate", "Security",    "BitLocker Drive Encryption drive was unlocked.", "Security"),
    6406: ("moderate", "Security",    "BitLocker Drive Encryption was activated.", "Security"),
    6407: ("moderate", "Security",    "BitLocker Drive Encryption was deactivated.", "Security"),
    6408: ("high",     "Security",    "BitLocker Drive Encryption detected auto-unlock has been disabled.", "Security"),
    6409: ("moderate", "Security",    "BitLocker Drive Encryption recovered from an unexpected shutdown.", "Security"),
    # -------------------------------------------------------
    # COMPLIANCE / GROUP POLICY
    # -------------------------------------------------------
    6144: ("moderate", "Compliance",  "Security policy in group policy objects was applied.", "Compliance"),
    6145: ("high",     "Compliance",  "Errors occurred while processing security policy in group policy objects.", "Compliance"),
    # -------------------------------------------------------
    # SYSTEM LOG EVENTS
    # -------------------------------------------------------
    41:   ("high",     "System",      "Kernel power failure. System was not shut down cleanly.", "Crash"),
    51:   ("high",     "Hardware",    "Disk error during a paging operation. Drive may be failing.", "Hardware"),
    104:  ("high",     "Security",    "Event log was cleared.", "Tampering"),
    1000: ("high",     "Crashes",     "Application crashed.", "Crash"),
    1001: ("low",      "System",      "Windows Error Reporting submitted a fault report.", "System"),
    1002: ("high",     "Crashes",     "Application hang detected.", "Crash"),
    1026: ("moderate", "Crashes",     ".NET runtime error.", "Crash"),
    1074: ("low",      "System",      "A process initiated a system shutdown or restart.", "System"),
    1076: ("moderate", "System",      "The reason for the unexpected shutdown was recorded.", "System"),
    4201: ("moderate", "Network",     "Network connection lost.", "Network"),
    6008: ("high",     "System",      "Unexpected shutdown. Power loss or system crash.", "Crash"),
    6013: ("low",      "System",      "System uptime reported.", "System"),
    7030: ("moderate", "System",      "A service is marked as an interactive service.", "System"),
    7031: ("moderate", "System",      "A service terminated unexpectedly.", "System"),
    7034: ("moderate", "System",      "A service terminated unexpectedly.", "System"),
    7036: ("low",      "System",      "A service started or stopped.", "System"),
    7038: ("moderate", "System",      "A service could not log on.", "System"),
    7040: ("low",      "System",      "Service start type was changed.", "System"),
    7045: ("high",     "Persistence", "A new service was installed. Review the service name and binary path.", "Persistence"),
    # -------------------------------------------------------
    # POWERSHELL
    # -------------------------------------------------------
    4103: ("high",     "Execution",   "PowerShell module logging: a command was executed. Review for encoded or obfuscated commands.", "Execution"),
    4104: ("high",     "Execution",   "PowerShell script block logging: a script was executed. Review for malicious activity.", "Execution"),
    # -------------------------------------------------------
    # RDP / TERMINAL SERVICES
    # -------------------------------------------------------
    1149: ("moderate", "Auth",        "Remote Desktop Services: User authentication succeeded.", "Auth"),
    9009: ("low",      "System",      "Desktop Window Manager has exited.", "System"),
    # -------------------------------------------------------
    # WINDOWS DEFENDER
    # -------------------------------------------------------
    1006: ("high",     "Security",    "Windows Defender detected malware or potentially unwanted software.", "Security"),
    1007: ("high",     "Security",    "Windows Defender took action against malware.", "Security"),
    1008: ("low",      "System",      "Windows Search index was reset and rebuilt.", "System"),
    1009: ("high",     "Security",    "Windows Defender restored an item from quarantine.", "Security"),
    1010: ("high",     "Security",    "Windows Defender could not restore an item from quarantine.", "Security"),
    1011: ("high",     "Security",    "Windows Defender could not delete a record from history.", "Security"),
    1012: ("high",     "Security",    "Windows Defender could not delete a record from history.", "Security"),
    1013: ("moderate", "Security",    "Windows Defender deleted malware history.", "Security"),
    1014: ("high",     "Security",    "Windows Defender could not delete expired items from history.", "Security"),
    1015: ("high",     "Security",    "Windows Defender detected a suspicious behavior.", "Security"),
    1116: ("high",     "Security",    "Windows Defender detected malware or potentially unwanted software.", "Security"),
    1117: ("high",     "Security",    "Windows Defender took action to protect the machine from malware.", "Security"),
    1118: ("high",     "Security",    "Windows Defender failed to take action on malware.", "Security"),
    1119: ("high",     "Security",    "Windows Defender encountered a critical error taking action on malware.", "Security"),
    1120: ("high",     "Security",    "Windows Defender encountered an error trying to take action on malware.", "Security"),
    2001: ("high",     "Security",    "Windows Defender antimalware definitions have failed to update.", "Security"),
    2003: ("moderate", "Security",    "Windows Defender antimalware definitions are out of date.", "Security"),
    2004: ("moderate", "Security",    "Windows Defender antimalware definitions loaded.", "Security"),
    2006: ("high",     "Security",    "Windows Defender failed to update definitions.", "Security"),
    2007: ("moderate", "Security",    "Windows Defender definitions are very out of date.", "Security"),
    2010: ("moderate", "Security",    "Windows Defender used dynamic signatures for protection.", "Security"),
    2012: ("moderate", "Security",    "Windows Defender failed to use dynamic signatures.", "Security"),
    3002: ("high",     "Security",    "Windows Defender real-time protection feature has encountered an error.", "Security"),
    3007: ("moderate", "Security",    "Windows Defender real-time protection has recovered.", "Security"),
    5001: ("high",     "Security",    "Windows Defender real-time protection is disabled.", "Security"),
    5004: ("high",     "Security",    "Windows Defender real-time protection feature configuration has changed.", "Security"),
    5007: ("high",     "Security",    "Windows Defender configuration changed. Check for unauthorized changes.", "Tampering"),
    5010: ("high",     "Security",    "Windows Defender scanning for malware and other unwanted software is disabled.", "Security"),
    5012: ("high",     "Security",    "Windows Defender scanning is disabled.", "Security"),
    # -------------------------------------------------------
    # APPLOCKER
    # -------------------------------------------------------
    8003: ("high",     "Execution",   "AppLocker allowed a file to run but would block it if in enforce mode.", "Execution"),
    8004: ("high",     "Execution",   "AppLocker blocked a file from running.", "Execution"),
    8006: ("high",     "Execution",   "AppLocker allowed a script or MSI file to run but would block it in enforce mode.", "Execution"),
    8007: ("high",     "Execution",   "AppLocker blocked a script or MSI file from running.", "Execution"),
    # -------------------------------------------------------
    # PRINT SPOOLER (PrintNightmare)
    # -------------------------------------------------------
    316:  ("high",     "Security",    "Print spooler failed to load a plug-in module. Could indicate PrintNightmare exploitation.", "Execution"),
    808:  ("high",     "Security",    "Print spooler failed to load a plug-in. Review for malicious printer drivers.", "Execution"),
    # -------------------------------------------------------
    # SYSMON
    # -------------------------------------------------------
    1:    ("high",     "Execution",   "A process was created. Check the command line and parent process for suspicious activity.", "Execution"),
    2:    ("moderate", "Tampering",   "A process changed a file creation timestamp. Common anti-forensics technique.", "Tampering"),
    3:    ("moderate", "Network",     "A network connection was initiated. Review the destination IP and port.", "Network"),
    4:    ("low",      "System",      "Sysmon service state changed.", "System"),
    5:    ("low",      "Execution",   "A process terminated.", "Execution"),
    6:    ("high",     "Execution",   "A kernel driver was loaded. Unsigned drivers can indicate rootkit activity.", "Execution"),
    7:    ("moderate", "Execution",   "A DLL or module was loaded into a process. Watch for DLL side-loading from unusual paths.", "Execution"),
    8:    ("high",     "Injection",   "A remote thread was created in another process. Classic process injection technique.", "Injection"),
    9:    ("moderate", "Hardware",    "Raw disk or volume access detected. Could indicate data exfiltration or disk forensics.", "Hardware"),
    10:   ("high",     "Injection",   "A process opened another process. Common in credential dumping tools like Mimikatz.", "Injection"),
    11:   ("low",      "FileSystem",  "A file was created.", "FileSystem"),
    12:   ("moderate", "Persistence", "A registry key or value was created or deleted.", "Persistence"),
    13:   ("moderate", "Persistence", "A registry value was set.", "Persistence"),
    14:   ("moderate", "Persistence", "A registry key or value was renamed.", "Persistence"),
    15:   ("high",     "Tampering",   "A named file stream was created. Alternate data streams are used to hide malicious payloads.", "Tampering"),
    16:   ("low",      "System",      "Sysmon configuration was updated.", "System"),
    17:   ("moderate", "Lateral",     "A named pipe was created. Malware uses named pipes for inter-process communication.", "Lateral"),
    18:   ("moderate", "Lateral",     "A named pipe connection was made.", "Lateral"),
    19:   ("high",     "Persistence", "A WMI event filter was registered. WMI subscriptions are a common persistence mechanism.", "Persistence"),
    20:   ("high",     "Persistence", "A WMI event consumer was registered.", "Persistence"),
    21:   ("high",     "Persistence", "A WMI consumer was bound to a filter. This completes a WMI subscription for persistence.", "Persistence"),
    22:   ("low",      "Network",     "A DNS query was made.", "Network"),
    23:   ("moderate", "FileSystem",  "A file was deleted.", "FileSystem"),
    24:   ("high",     "Exfiltration","System clipboard contents changed. Could indicate data theft via clipboard.", "Exfiltration"),
    25:   ("high",     "Injection",   "Process tampering detected. Possible process hollowing or herpaderping attack.", "Injection"),
    26:   ("moderate", "FileSystem",  "A file deletion was detected.", "FileSystem"),
    27:   ("high",     "FileSystem",  "Sysmon blocked creation of an executable file.", "FileSystem"),
    28:   ("high",     "Tampering",   "Sysmon blocked file shredding. A tool attempted to destroy evidence.", "Tampering"),
    29:   ("high",     "FileSystem",  "A new executable file was created.", "FileSystem"),
    255:  ("low",      "System",      "Sysmon encountered an internal error.", "System"),
    # -------------------------------------------------------
    # NETWORK
    # -------------------------------------------------------
    36887:("moderate", "Network",     "TLS fatal alert received from remote endpoint.", "Network"),
    36888:("moderate", "Network",     "TLS error generated.", "Network"),
    # -------------------------------------------------------
    # CAPI2 / CRYPTOGRAPHY
    # -------------------------------------------------------
    257:  ("moderate", "Security",    "A cryptographic operation failed. Usually a certificate validation error.", "Security"),
    258:  ("moderate", "Security",    "A cryptographic operation failed.", "Security"),
    # -------------------------------------------------------
    # WINDOWS SEARCH
    # -------------------------------------------------------
    10023:("low",      "System",      "Windows Search indexer stopped.", "System"),
    # -------------------------------------------------------
    # WINDOWS LICENSE / ACTIVATION
    # -------------------------------------------------------
    8198: ("low",      "System",      "License activation failed. The machine could not reach the activation server.", "System"),
}

# Windows level text to severity mapping
LEVEL_MAP: Dict[str, str] = {
    "critical":    "high",
    "error":       "high",
    "warning":     "moderate",
    "information": "low",
    "verbose":     "low",
    "audit failure": "high",
    "audit success": "low",
}

def _level_to_severity(level_str: str) -> str:
    return LEVEL_MAP.get((level_str or "").strip().lower(), "low")

def parse_windows_event_block(block: str) -> Optional[Dict[str, Any]]:
    """
    Parse one Windows Event Viewer text block into a structured dict.
    Expected format:
        Log Name: System
        Source: Service Control Manager
        Date: 2025-02-14 09:00:01
        Event ID: 7036
        Level: Information
        Description:
        The Windows Update service entered the running state.
    Returns None if block does not look like a Windows event.
    """
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return None

    fields: Dict[str, str] = {}
    desc_lines: List[str] = []
    in_desc = False

    for line in lines:
        if in_desc:
            desc_lines.append(line)
            continue
        if line.lower().startswith("description:"):
            in_desc = True
            remainder = line[len("description:"):].strip()
            if remainder:
                desc_lines.append(remainder)
            continue
        for key in ("log name", "source", "date", "event id", "level"):
            if line.lower().startswith(key + ":"):
                fields[key] = line[len(key)+1:].strip()
                break

    if "event id" not in fields and "level" not in fields:
        return None

    event_id_raw = fields.get("event id", "")
    try:
        event_id = int(event_id_raw)
    except ValueError:
        event_id = None

    level_str = fields.get("level", "")
    description = " ".join(desc_lines).strip()
    source = fields.get("source", "")
    date = fields.get("date", "")
    log_name = fields.get("log name", "")

    # Build entry text for display
    entry_parts = []
    if date:
        entry_parts.append(date)
    if source:
        entry_parts.append(source)
    if event_id:
        entry_parts.append(f"EventID {event_id}")
    entry = "  ".join(entry_parts)

    # Determine severity and explanation
    if event_id and event_id in EVENT_ID_MAP:
        severity, section, explanation, threat = EVENT_ID_MAP[event_id]

    else:
        severity = _level_to_severity(level_str)
        section = log_name or "General"
        threat = "None"
        explanation = description or f"{source} logged a {level_str.lower() or 'system'} event."

    return {
        "entry": entry,
        "simplified": description[:180] if description else entry[:180],
        "severity": severity,
        "section": section,
        "explanation": explanation,
        "evidence": [],
        "os": "Windows",
        "threat": threat,
        "confidence": 0.9 if event_id in (EVENT_ID_MAP or {}) else 0.4,
        "matched_patterns": [{"event_id": event_id}] if event_id else [],
        "timestamp": date,
        "source": source,
        "event_id": event_id,
        "log_name": log_name,
    }


def parse_windows_event_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Split text into Windows event blocks and parse each one.
    Blocks are separated by a blank line or a new 'Log Name:' line.
    """
    results = []
    current: List[str] = []

    for line in text.splitlines():
        if line.strip().lower().startswith("log name:") and current:
            block = "\n".join(current)
            parsed = parse_windows_event_block(block)
            if parsed:
                results.append(parsed)
            current = [line]
        else:
            current.append(line)

    if current:
        block = "\n".join(current)
        parsed = parse_windows_event_block(block)
        if parsed:
            results.append(parsed)

    return results


def looks_like_windows_event_log(text: str) -> bool:
    """
    Quick heuristic: does this text look like a Windows Event Viewer export?
    """
    lower = text.lower()
    return (
        "log name:" in lower and
        "event id:" in lower and
        "level:" in lower
    )
