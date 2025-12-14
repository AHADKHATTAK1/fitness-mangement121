import json
import os
import hashlib
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.users = self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)

    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def user_exists(self, username):
        return username in self.users

    def validate_referral(self, code):
        """Check if referral code is valid.
        For now, we accept a master code 'VIP2025' or 'FREEACCESS'."""
        valid_codes = ['VIP2025', 'FREE']
        return code and code.upper() in valid_codes

    def create_user(self, username, password, referral_code=None):
        if username in self.users:
            return False
        
        if referral_code and self.validate_referral(referral_code):
            plan = 'free_lifetime'
            expiry = '2099-12-31' # Lifetime
        else:
            plan = 'standard'
            expiry = None # Not active yet, requires payment
        
        self.users[username] = {
            'password': self.hash_password(password),
            'joined_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'referral_code': referral_code,
            'plan': plan,
            'subscription_expiry': expiry
        }
        self.save_users()
        return True

    def is_subscription_active(self, username):
        if username not in self.users: return False
        user = self.users[username]
        
        # Free/Admin users always active
        if user.get('plan') == 'free_lifetime': return True
        
        expiry_str = user.get('subscription_expiry')
        if not expiry_str: return False
        
        expiry_date = datetime.strptime(expiry_str, '%Y-%m-%d')
        return datetime.now() <= expiry_date

    def renew_subscription(self, username, days=30):
        if username in self.users:
            new_expiry = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            self.users[username]['subscription_expiry'] = new_expiry
            
            # Record the transaction
            self.record_payment(username, 60.00, 'Credit Card')
            
            self.save_users()
            return True
        return False

    def record_payment(self, username, amount, method):
        if username not in self.users: return
        
        if 'payments' not in self.users[username]:
            self.users[username]['payments'] = []
            
        self.users[username]['payments'].append({
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'amount': amount,
            'method': method,
            'status': 'Completed'
        })
        # Save is handled by the caller (renew_subscription) or we can save here
        # But renew calls save, so it's fine.

    def verify_user(self, username, password):
        if username not in self.users:
            return False
        
        # Handle legacy plain text passwords if migrating (optional, but good practice)
        stored = self.users[username]
        if stored['password'] == self.hash_password(password):
            return True
        return False

    def set_payment_pending(self, username, proof_filename):
        if username in self.users:
            self.users[username]['subscription_status'] = 'pending'
            self.users[username]['payment_proof'] = proof_filename
            self.save_users()
            return True
        return False

    def get_pending_approvals(self):
        pending = []
        for email, data in self.users.items():
            if data.get('subscription_status') == 'pending':
                pending.append({
                    'username': email,
                    'proof': data.get('payment_proof'),
                    'joined': data.get('joined_at')
                })
        return pending

    def approve_manual_payment(self, username):
        if username in self.users:
            self.users[username]['subscription_status'] = 'active'
            # Give 30 days
            new_expiry = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
            self.users[username]['subscription_expiry'] = new_expiry
            
            # Record
            self.record_payment(username, 2000.00, 'Manual/JazzCash') # 2000 PKR as per user Django
            
            self.save_users()
            return True
        return False

    def get_user_data_file(self, username):
        """Return the filename for this user's gym data"""
        # Sanitize username to be safe filename
        safe_name = "".join([c for c in username if c.isalpha() or c.isdigit() or c in ('@', '.', '_')]).strip()
        return f"gym_data/{safe_name}.json"
