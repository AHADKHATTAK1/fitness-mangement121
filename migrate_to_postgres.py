"""
Migration script: JSON files → PostgreSQL database
Migrates all existing data from JSON files to PostgreSQL
"""

import json
import os
from datetime import datetime
from models import User, Gym, Member, Fee, Attendance, Expense, init_db, get_session
from auth_manager import AuthManager
from werkzeug.security import generate_password_hash

def migrate_data():
    """Main migration function"""
    print("🔄 Starting migration from JSON to PostgreSQL...")
    
    # Initialize database (create tables)
    print("📊 Creating database tables...")
    init_db()
    session = get_session()
    
    try:
        # Step 1: Migrate users from users.json
        print("\n👤 Migrating users...")
        migrate_users(session)
        
        # Step 2: Migrate gym data for each user
        print("\n🏋️ Migrating gym data...")
        migrate_gyms(session)
        
        session.commit()
        print("\n✅ Migration completed successfully!")
        print(f"   Users: {session.query(User).count()}")
        print(f"   Gyms: {session.query(Gym).count()}")
        print(f"   Members: {session.query(Member).count()}")
        print(f"   Fees: {session.query(Fee).count()}")
        print(f"   Attendance: {session.query(Attendance).count()}")
        print(f"   Expenses: {session.query(Expense).count()}")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def migrate_users(session):
    """Migrate users from users.json"""
    users_file = 'users.json'
    
    if not os.path.exists(users_file):
        print("   ⚠️  users.json not found, skipping user migration")
        return
    
    with open(users_file, 'r') as f:
        users_data = json.load(f)
    
    for email, user_data in users_data.items():
        # Check if user already exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            print(f"   ⏭️  User {email} already exists, skipping")
            continue
        
        user = User(
            email=email,
            password_hash=user_data.get('password', ''),
            role=user_data.get('role', 'admin')
        )
        session.add(user)
        print(f"   ✓ Migrated user: {email}")
    
    session.flush()  # Get user IDs

def migrate_gyms(session):
    """Migrate gym data from gym_data/*.json files"""
    gym_data_dir = 'gym_data'
    
    if not os.path.exists(gym_data_dir):
        print("   ⚠️  gym_data directory not found, skipping gym migration")
        return
    
    # Get all JSON files in gym_data directory
    json_files = [f for f in os.listdir(gym_data_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        email = json_file.replace('.json', '')
        filepath = os.path.join(gym_data_dir, json_file)
        
        # Get user
        user = session.query(User).filter_by(email=email).first()
        if not user:
            print(f"   ⚠️  User {email} not found, skipping gym data")
            continue
        
        # Load gym data
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Create gym
        gym_details = data.get('gym_details', {})
        gym = Gym(
            user_id=user.id,
            name=gym_details.get('name', 'Gym Manager'),
            logo_url=gym_details.get('logo'),
            currency=gym_details.get('currency', 'Rs')
        )
        session.add(gym)
        session.flush()  # Get gym ID
        print(f"   ✓ Created gym: {gym.name} for {email}")
        
        # Migrate members
        members_data = data.get('members', {})
        member_map = {}  # Map old member_id to new Member object
        
        for old_id, member_data in members_data.items():
            # Sanitize joined_date (fix typos like '12025' -> '2025')
            joined_date_str = member_data.get('joined_date', '')
            if joined_date_str:
                # Fix common typo: extra '1' at start of year
                if joined_date_str.startswith('1202'):
                    joined_date_str = joined_date_str[1:]  # Remove first '1'
                
                try:
                    joined_date = datetime.strptime(joined_date_str, '%Y-%m-%d').date()
                except:
                    # If still fails, use today's date
                    joined_date = datetime.now().date()
            else:
                joined_date = datetime.now().date()
            
            member = Member(
                gym_id=gym.id,
                name=member_data.get('name'),
                phone=member_data.get('phone'),
                email=member_data.get('email', ''),
                photo_url=member_data.get('photo'),
                membership_type=member_data.get('membership_type', 'Gym'),
                joined_date=joined_date,
                is_active=member_data.get('active', True),
                is_trial=member_data.get('is_trial', False),
                trial_end_date=datetime.strptime(member_data['trial_end_date'], '%Y-%m-%d').date() 
                    if member_data.get('trial_end_date') else None
            )
            session.add(member)
            member_map[old_id] = member
        
        session.flush()  # Get member IDs
        print(f"     ✓ Migrated {len(members_data)} members")
        
        # Migrate fees
        fees_data = data.get('fees', {})
        fee_count = 0
        
        for old_member_id, months in fees_data.items():
            if old_member_id not in member_map:
                continue
            
            member = member_map[old_member_id]
            
            for month, fee_data in months.items():
                # Handle both old string format and new dict format
                if isinstance(fee_data, str):
                    try:
                        paid_date = datetime.strptime(fee_data, '%Y-%m-%d %H:%M:%S')
                    except:
                        paid_date = datetime.now()  # Default to now if parse fails
                    amount = 0  # Default amount for old format
                else:
                    date_str = fee_data.get('date')
                    if date_str:
                        try:
                            paid_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                        except:
                            paid_date = datetime.now()
                    else:
                        # If no date, use first day of the month
                        paid_date = datetime.strptime(f"{month}-01 00:00:00", '%Y-%m-%d %H:%M:%S')
                    amount = fee_data.get('amount', 0)
                
                fee = Fee(
                    member_id=member.id,
                    month=month,
                    amount=amount,
                    paid_date=paid_date
                )
                session.add(fee)
                fee_count += 1
        
        print(f"     ✓ Migrated {fee_count} fee records")
        
        # Migrate attendance (if exists)
        attendance_data = data.get('attendance', {})
        attendance_count = 0
        
        for old_member_id, records in attendance_data.items():
            if old_member_id not in member_map:
                continue
            
            member = member_map[old_member_id]
            
            for record in records:
                # Handle both old string format and new dict format
                if isinstance(record, str):
                    check_in_time = datetime.strptime(record, '%Y-%m-%d %H:%M:%S')
                    emotion = None
                    confidence = None
                else:
                    check_in_time = datetime.strptime(record.get('timestamp'), '%Y-%m-%d %H:%M:%S')
                    emotion = record.get('emotion')
                    confidence = record.get('confidence')
                
                attendance = Attendance(
                    member_id=member.id,
                    check_in_time=check_in_time,
                    emotion=emotion,
                    confidence=confidence
                )
                session.add(attendance)
                attendance_count += 1
        
        print(f"     ✓ Migrated {attendance_count} attendance records")
        
        # Migrate expenses
        expenses_data = data.get('expenses', {})
        
        for expense_id, expense_data in expenses_data.items():
            expense = Expense(
                gym_id=gym.id,
                category=expense_data.get('category'),
                amount=expense_data.get('amount'),
                date=datetime.strptime(expense_data.get('date'), '%Y-%m-%d').date(),
                description=expense_data.get('description', '')
            )
            session.add(expense)
        
        print(f"     ✓ Migrated {len(expenses_data)} expenses")

if __name__ == '__main__':
    migrate_data()
