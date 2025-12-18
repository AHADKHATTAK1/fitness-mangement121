"""
Database-backed Authentication Manager
Uses PostgreSQL User table instead of JSON files
"""

from models import User, get_session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

class AuthManager:
    def __init__(self):
        self.session = get_session()
    
    def hash_password(self, password):
        """Hash password using werkzeug"""
        return generate_password_hash(password)
    
    def check_password(self, password_hash, password):
        """Verify password"""
        return check_password_hash(password_hash, password)
    
    def user_exists(self, username):
        """Check if user exists"""
        user = self.session.query(User).filter_by(email=username).first()
        return user is not None
    
    def validate_referral(self, code):
        """Check if referral code is valid"""
        valid_codes = ['VIP2025', 'FREE']
        return code and code.upper() in valid_codes
    
    def create_user(self, username, password, referral_code=None):
        """Create a new user"""
        if self.user_exists(username):
            return False
        
        user = User(
            email=username,
            password_hash=self.hash_password(password),
            role='admin'
        )
        
        self.session.add(user)
        self.session.commit()
        return True
    
    def verify_user(self, username, password):
        """Verify user credentials"""
        user = self.session.query(User).filter_by(email=username).first()
        if not user:
            return False
        
        return self.check_password(user.password_hash, password)
    
    def get_user_data_file(self, username):
        """Get user's data file path (legacy - not used with PostgreSQL)"""
        return f"gym_data/{username}.json"
    
    # Password Reset Methods
    def generate_reset_code(self, username):
        """Generate a 6-digit reset code"""
        user = self.session.query(User).filter_by(email=username).first()
        if not user:
            return None
        
        code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        expiry = datetime.now() + timedelta(minutes=15)
        
        # Store in user object (we'll add these fields to User model)
        # For now, return the code directly
        return code
    
    def verify_reset_code(self, username, code):
        """Verify reset code (simplified for now)"""
        # In production, check expiry and stored code
        return True  # Simplified
    
    def update_password(self, username, new_password):
        """Update user password"""
        user = self.session.query(User).filter_by(email=username).first()
        if not user:
            return False
        
        user.password_hash = self.hash_password(new_password)
        self.session.commit()
        return True
    
    def __del__(self):
        """Close database session"""
        if hasattr(self, 'session'):
            self.session.close()
