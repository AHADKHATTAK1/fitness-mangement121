
import json
import pandas as pd
import os
from gym_manager import GymManager

# Path to the specific gym data file we want to migrate
DATA_FILE = r"c:\Users\hp\Desktop\tracker software\gym_data\zaidanfitnessgym@gmail.com.json"

def export_data():
    print(f"Reading data from: {DATA_FILE}")
    
    if not os.path.exists(DATA_FILE):
        print("❌ Error: Data file not found!")
        return

    try:
        # Load the data directly
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            
        members = data.get('members', {})
        print(f"Found {len(members)} members.")
        
        # Prepare list for DataFrame
        export_list = []
        for m_id, m_data in members.items():
            export_list.append({
                'Name': m_data.get('name'),
                'Phone': m_data.get('phone'),
                'Email': m_data.get('email', ''),
                'Membership Type': m_data.get('membership_type', 'Gym'),
                'Joined Date': m_data.get('joined_date')
            })
            
        if not export_list:
            print("⚠️ No members found to export.")
            return

        # Create DataFrame
        df = pd.read_json(json.dumps(export_list)) 
        # (Using json.dumps -> read_json is a safe way to handle potential mixed types, or just pd.DataFrame)
        df = pd.DataFrame(export_list)
        
        # Save to Excel
        output_file = "cloud_migration_data.xlsx"
        df.to_excel(output_file, index=False)
        
        print(f"\n✅ Success! Exported {len(export_list)} members to '{output_file}'")
        print("👉 Now: Go to your Cloud App -> Bulk Import -> Upload this file.")
        
    except Exception as e:
        print(f"❌ Error exporting data: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    export_data()
