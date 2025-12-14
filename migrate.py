import json
import os
import shutil
from auth_manager import AuthManager

def migrate():
    print("Starting migration...")
    
    # 1. Load existing data
    if not os.path.exists('gym_data.json'):
        print("No gym_data.json found. Skipping migration.")
        return

    with open('gym_data.json', 'r') as f:
        data = json.load(f)

    admin = data.get('admin')
    if not admin:
        print("No admin found in data.")
        return

    username = admin['username']
    password = admin['password']
    
    print(f"Found admin: {username}")

    # 2. Initialize AuthManager (creates users.json)
    auth = AuthManager()
    
    # 3. Create user in new system
    # We use the raw password because AuthManager hashes it
    # But wait, create_user hashes it.
    if auth.create_user(username, password, referral_code="MIGRATED"):
        print(f"User {username} created in users.json")
    else:
        print(f"User {username} already exists in users.json")

    # 4. Move data file
    # We want to preserve the data, so we copy it to the user's specific file
    user_data_file = auth.get_user_data_file(username)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(user_data_file), exist_ok=True)
    
    # Copy file content
    with open(user_data_file, 'w') as f:
        json.dump(data, f, indent=2)
        
    print(f"Data copied to {user_data_file}")
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
