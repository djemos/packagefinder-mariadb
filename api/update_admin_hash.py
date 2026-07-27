#!/usr/bin/env python3
import hashlib
import getpass
import re
import os

def update_stats_hash():
    stats_file = "stats.py"
    PASSWORD_SALT = "your_password"
    
    print("=== Admin Hash Generator ===")
    print("Type your password normally below (special characters @#$! are allowed).")
    print("Do NOT wrap your password in quotes.")
    print("----------------------------------------------------------------------")
    
    # 1. getpass securely reads exactly what you type without terminal interference
    password = getpass.getpass("Enter Admin Password: ")
    
    if not password:
        print("[-] Error: Password cannot be empty.")
        return

    # 2. Replicate your exact verify_password logic: plain_password + PASSWORD_SALT
    # We use .strip() to clean accidental trailing newlines or spaces
    salted = password.strip() + PASSWORD_SALT
    new_hash = hashlib.sha256(salted.encode('utf-8')).hexdigest()
    
    # 3. Verify stats.py exists
    if not os.path.exists(stats_file):
        print(f"[-] Error: '{stats_file}' not found in this directory.")
        print("    Please make sure this script is placed in the same folder as stats.py.")
        return

    # 4. Read the file
    with open(stats_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 5. Automatically replace the values
    salt_line = f'PASSWORD_SALT = "{PASSWORD_SALT}"'
    hash_line = f'ADMIN_PASSWORD_HASH = "{new_hash}"'
    
    if "PASSWORD_SALT" in content:
        content = re.sub(r'PASSWORD_SALT\s*=\s*["\'].*?["\']', salt_line, content)
    else:
        content += f"\n{salt_line}"
        
    if "ADMIN_PASSWORD_HASH" in content:
        content = re.sub(r'ADMIN_PASSWORD_HASH\s*=\s*["\'].*?["\']', hash_line, content)
    else:
        content += f"\n{hash_line}"

    # 6. Save the updated file
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("\n[+] Success! Your 'stats.py' file has been updated automatically.")
    print(f"    New generated hash: {new_hash}")

if __name__ == "__main__":
    update_stats_hash()
