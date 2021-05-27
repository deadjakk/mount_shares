#!/usr/bin/python3

import os
import sys # Used by len, exit, etc
import argparse # Parser for command-line options, arguments and sub-commands
import logging
import ntpath
import subprocess
from impacket import smb
#from impacket.smb3structs import FILE_READ_DATA # unsure if I need this...
from impacket.smbconnection import SessionError
from impacket.smbconnection import SMBConnection # used impacket to connect to smb

smb_share_name = None
smb_server = None

############################################
# by Leon Johnson aka @sho_luv
#
# This code uses Impacket library to mount remote 
# shares locally. This allows us to use tools like
# grep and other linux tools to search the shares
# for sensitive information.
#
# This program is used to mount cifs shares
# it will only list readable shares unless 
# -show option is provided. To mount shares
# It will create a directory named after
# the hostname and mount readable shares
# inside that dir.
#
# Debugging:
#       python -m pdb program.py
#
# this program will do the following:
#
# [x] list readable shares for supplied user
# [x] mount readable shares locally
# [ ] mount shares with spaces correctly
#     see CGYFS002 for example (might have fixed this indirectly)
# [x] verify creds used are valid
# [x] remove crackmapexec dependency
# [x] fixed /etc/resolve.conf dependency
# [x] change default to READONLY changed with -write option
# [x] added auth file support
# [ ] add kerberos support to mounting shares
# [ ] remove mount command dependency
# [ ] add hash support after remove mount dependency
#       Can't use mount command with hashes

# ----------------------------------
# Colors
# ----------------------------------
NOCOLOR='\033[0m'
RED='\033[0;31m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
LIGHTGRAY='\033[0;37m'
DARKGRAY='\033[1;30m'
LIGHTRED='\033[1;31m'
LIGHTGREEN='\033[1;32m'
YELLOW='\033[1;33m'
LIGHTBLUE='\033[1;34m'
LIGHTPURPLE='\033[1;35m'
LIGHTCYAN='\033[1;36m'
WHITE='\033[1;37m'

def print_info():
        print(LIGHTBLUE+"SMB\t"+NOCOLOR+ipAddress+"\t"+options.port+"\t"+hostname, end = '')

def print_shares(connection):

        permissions = []
        shares = []
        output = []

        for share in connection.listShares():
            share_name = share['shi1_netname'][:-1]
            share_remark = share['shi1_remark'][:-1]
            share_info = {'name': share_name, 'remark': share_remark, 'access': []}
            read = False
            write = False

            try:
                connection.listPath(share_name, '*')
                read = True
                share_info['access'].append('READ')
            except SessionError:
                pass

            try:
                connection.createDirectory(share_name, "\\mytempdir_washere")
                connection.deleteDirectory(share_name, "\\mytempdir_washere")
                write = True
                share_info['access'].append('WRITE')
            except SessionError:
                pass

            permissions.append(share_info)

        for share in permissions:
            name   = share['name']
            remark = share['remark']
            perms  = share['access']

            #print((u'{:<15} {:<15} {}'.format(name, ','.join(perms), remark)))
            output = (u'{:<15} {:<15} {}'.format(name, ','.join(perms), remark))
            shares.append(''.join(output))

        if options.show is False:
            print_info()
            print(LIGHTGREEN+"\t[+] "+NOCOLOR+"Enumerated readable shares")
            print_info()
            print(YELLOW+"\tShare\t\tPermissions\tRemark"+NOCOLOR)
            print_info()
            print(YELLOW+"\t-----\t\t-----------\t------"+NOCOLOR)
            for share in shares:

                # no need to mount IPC share so we skip it!
                if re.search("IPC", share):
                   continue

                if re.search("READ", share):
                    print_info()
                    print(YELLOW+"\t"+share+NOCOLOR)
                    if options.m is True:
                        mount(share)

                    elif options.u is True:
                        unmount(share)

        else:
            print_info()
            print(LIGHTGREEN+"\t[+] "+NOCOLOR+"Enumerated all shares")
            print_info()
            print(YELLOW+"\tShare\t\tPermissions\tRemark"+NOCOLOR)
            print_info()
            print(YELLOW+"\t-----\t\t-----------\t------"+NOCOLOR)
            for share in shares:
                print_info()
                print(YELLOW+"\t"+share+NOCOLOR)

        print(NOCOLOR)

def mount(shares):

    if re.search("READ", shares):
        share = re.findall(r"[\w\.\$\-]+", shares, flags=re.U)

        # I created two variables because I wanted to name the share after the hostname
        # however if the hostname doesn't resolve the mount command errors out
        # so I use the IP address to mount the share and the hostname to name the local shares
        # otherwise you have to ensure the hostname resolves in /etc/resolve.conf
        # by adding search i.e. echo -n "search domain.local" >> /etc/resolve.conf
        hostnameDirectory = hostname+"/"+share[0] 
        ipDirectory = ipAddress+"/"+share[0] 

        # check if dir already exist if not make it
        if not os.path.exists(hostnameDirectory):
            os.makedirs(hostnameDirectory)

        # check if dir is empty
        if not os.listdir(hostnameDirectory):
            try:
                """
                # need to figure out how to use createMountPoint from smbconnection.py ->
                # https://github.com/SecureAuthCorp/impacket/blob/a16198c3312d8cfe25b329907b16463ea3143519/impacket/smbconnection.py#L861
                # I want to mount a remote network share locally using the createMountPoint function. 
                # However I'm unsure how to use this function. It's defined as follows:
                # def createMountPoint(self, tid, path, target):
                    #
                    #creates a mount point at an existing directory
                    #:param int tid: tree id of current connection
                    #:param string path: directory at which to create mount point (must already exist)
                    #:param string target: target address of mount point
                    
                #smbClient.createMountPoint( smbClient, directory, hostname)
                """
                if not options.write:
                    mountCommand = 'mount -r -t cifs //'+ipDirectory+' ./'+hostnameDirectory+' -o username='+username+',password=\''+password+'\''
                else:
                    print_info()
                    print(LIGHTGREEN+"\t[+] "+NOCOLOR, end = '')
                    print(RED+"Caution you mounted these shares as WRITABLE"+NOCOLOR)
                    mountCommand = 'mount -t cifs //'+ipDirectory+' ./'+hostnameDirectory+' -o username='+username+',password=\''+password+'\''
                subprocess.call([mountCommand], shell=True, stdout=subprocess.PIPE, universal_newlines=True)
                print_info()
                print(LIGHTGREEN+"\t[+] "+NOCOLOR, end = '')
                print("Mounted "+hostnameDirectory+" Successfully!")
            except:
                print("Unable to mount share: //"+hostnameDirectory)

        else:
            print_info()
            print(RED+"\t[+] "+NOCOLOR, end = '')
            print(directory+" is not empty directory. Unable to mount")
            return
                

def unmount(shares):

    if re.search("READ", shares):

        share = re.findall(r"[\w\.\$\-]+", shares, flags=re.U)
        directory = hostname+"/"+share[0]

        # check if dir exist
        if not os.path.exists(directory):
            print_info()
            print(RED+"\t[+] "+NOCOLOR, end = '')
            print("Can't unmount "+directory+" because it is doesn't exist!")
        else:
            try:
                subprocess.call(['umount',directory], shell=True, stdout=subprocess.PIPE, universal_newlines=True)
                #subprocess.call(['umount',directory])
                print_info()
                print(LIGHTGREEN+"\t[+] "+NOCOLOR, end = '')
                print("Unmounted: "+directory)
                subprocess.call(['rmdir',directory])
                print_info()
                print(LIGHTGREEN+"\t[+] "+NOCOLOR, end = '')
                print("Removed: "+directory)
            except:
                print_info()
                print("Unable to unmount share: "+directory)


class AuthFileSyntaxError(Exception):

    '''raised by load_smbclient_auth_file if it encounters a syntax error
    while loading the smbclient-style authentication file.'''

    def __init__(self, path, lineno, reason):
        self.path=path
        self.lineno=lineno
        self.reason=reason

    def __str__(self):
        return 'Syntax error in auth file %s line %d: %s' % (
            self.path, self.lineno, self.reason )

def load_smbclient_auth_file(path):

    '''Load credentials from an smbclient-style authentication file (used by
    smbclient, mount.cifs and others).  returns (domain, username, password)
    or raises AuthFileSyntaxError or any I/O exceptions.'''

    lineno=0
    domain=None
    username=None
    password=None
    for line in open(path):
        lineno+=1

        line = line.strip()

        if line.startswith('#') or line=='':
            continue

        parts = line.split('=',1)
        if len(parts) != 2:
            raise AuthFileSyntaxError(path, lineno, 'No "=" present in line')

        (k,v) = (parts[0].strip(), parts[1].strip())

        if k=='username':
            username=v
        elif k=='password':
            password=v
        elif k=='domain':
            domain=v
        else:
            raise AuthFileSyntaxError(path, lineno, 'Unknown option %s' % repr(k))

    return (domain, username, password)


if __name__ == '__main__':

    banner = """
        x-----------x
        | MOUNT     |
        | THEM      |
        | SHARES    |
        x-----------x
               ||
        (\__/) ||
        (•ㅅ•) ||
        / 　 づ
    """

    parser = argparse.ArgumentParser(description="Tool to list shares and/or create local dir to mount them for searching locally")

    parser.add_argument('target', action='store', help='[[domain/]username[:password]@]<targetName or address>')
    parser.add_argument('-show', action='store_true', help='Show all shares available (Default only show READ access shares)')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m','-mount', action='store_true', help='Mount target shares locally')
    group.add_argument('-u','-unmount', action='store_true', help='Unmount shares for target locally')

    parser.add_argument('-debug', action='store_true', help='Turn DEBUG output ON')
    parser.add_argument('-write', action='store_true', help='Mount shares as WRITABLE (Default READ ONLY')

    group = parser.add_argument_group('authentication')
    group.add_argument('-A', action="store", metavar = "authfile", help="smbclient/mount.cifs-style authentication file. "
                                                                        "See smbclient man page's -A option.")
    group = parser.add_argument_group('connection')
    group.add_argument('-port', choices=['139', '445'], nargs='?', default='445', metavar="destination port",
                       help='Destination port to connect to SMB Server')



    if len(sys.argv)==1:
        print( banner )
        parser.print_help()
        sys.exit(1)

    options = parser.parse_args()

    import re

    domain, username, password, address = re.compile('(?:(?:([^/@:]*)/)?([^@:]*)(?::([^@]*))?@)?(.*)').match(
        options.target).groups('')

    # In case the password contains '@'
    if '@' in address:
        password = password + '@' + address.rpartition('@')[0]
        address = address.rpartition('@')[2]

    if options.A is not None:
        (domain, username, password) = load_smbclient_auth_file(options.A)
        logging.debug('loaded smbclient auth file: domain=%s, username=%s, password=%s' % (repr(domain), repr(username), repr(password)))

    if domain is None:
        domain = ''

    if password == '' and username != '':
        from getpass import getpass
        password = getpass("Password:")

    try:
        smbClient = SMBConnection(address, address, sess_port=int(options.port))
        smbClient.login(username, password, domain)

        # get passed credentials
        userName, password, domain, lmhash, nthash, aesKey, TGT, TGS = smbClient.getCredentials()

        # get computer information
        hostname = smbClient.getServerName()
        ipAddress = smbClient.getRemoteHost()
        domain = smbClient.getServerDomain()
        fqdn = smbClient.getServerDNSDomainName()
        osVersion = smbClient.getServerOS()

        print_info()
        print(LIGHTBLUE+"\t[*] "+NOCOLOR, end = '')
        print(osVersion+" (name:"+hostname+") (domain:"+domain+")") 
        print_info()

        if not domain:
            print(LIGHTGREEN+"\t[+] "+NOCOLOR+hostname+"/"+userName+":"+password)
        else:
            print(LIGHTGREEN+"\t[+] "+NOCOLOR+domain+"/"+userName+":"+password)

        """
        print(smbClient.getServerName()) # get hostname
        print(smbClient.getRemoteHost()) # get IP address
        print(smbClient.getServerDomain()) # get domain name
        print(smbClient.getServerDNSDomainName()) # get full resolvable domain name
        print(smbClient.getServerDNSHostName()) # get domain name
        print(smbClient.getServerOS()) # get verion and build info
        #print(smbClient.getCredentials()) # get passed credentials
        #print(smbClient.listShares()) # get list shares
        smbClient.createMountPoint(smbClient, './', test_dir)
        """

        # default print only readable shares
        print_shares(smbClient)
        
    except Exception as e:
        if logging.getLogger().level == logging.DEBUG:
            import traceback
            traceback.print_exc()
        logging.error(str(e))
