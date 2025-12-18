"""
Database-backed Gym Manager
Uses PostgreSQL via SQLAlchemy instead of JSON files
"""

from models import User, Gym, Member, Fee, Attendance, Expense, get_session
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, extract
from sqlalchemy.exc import IntegrityError

class GymManager:
    def __init__(self, user_email):
        """Initialize with user's email"""
        self.user_email = user_email
        self.session = get_session()
        
        # Get or create user's gym
        user = self.session.query(User).filter_by(email=user_email).first()
        if user:
            self.gym = self.session.query(Gym).filter_by(user_id=user.id).first()
            if not self.gym:
                # Create default gym for user
                self.gym = Gym(
                    user_id=user.id,
                    name='Gym Manager',
                    currency='Rs'
                )
                self.session.add(self.gym)
                self.session.commit()
        else:
            self.gym = None
    
    def get_gym_details(self) -> Dict:
        """Get gym name, logo, and currency"""
        if not self.gym:
            return {'name': 'Gym Manager', 'logo': None, 'currency': 'Rs'}
        
        return {
            'name': self.gym.name,
            'logo': self.gym.logo_url,
            'currency': self.gym.currency
        }
    
    def update_gym_details(self, name: str, logo_path: Optional[str] = None, currency: str = 'Rs') -> bool:
        """Update gym name, logo, and currency"""
        if not self.gym:
            return False
        
        self.gym.name = name
        self.gym.currency = currency
        if logo_path:
            self.gym.logo_url = logo_path
        
        self.session.commit()
        return True
    
    def add_member(self, name: str, phone: str, photo: str = None, membership_type: str = 'Gym', 
                   joined_date: str = None, is_trial: bool = False, email: str = None) -> int:
        """Add a new member"""
        if not self.gym:
            return 0
        
        if not joined_date:
            joined_date = datetime.now().strftime('%Y-%m-%d')
        
        trial_end = None
        if is_trial:
            trial_end = (datetime.strptime(joined_date, '%Y-%m-%d') + timedelta(days=3)).date()
        
        member = Member(
            gym_id=self.gym.id,
            name=name,
            phone=phone,
            email=email or '',
            photo_url=photo,
            membership_type=membership_type,
            joined_date=datetime.strptime(joined_date, '%Y-%m-%d').date(),
            is_trial=is_trial,
            trial_end_date=trial_end
        )
        
        self.session.add(member)
        self.session.commit()
        return member.id
    
    def update_member(self, member_id: str, name: str, phone: str, membership_type: str, 
                     joined_date: Optional[str] = None, email: str = None) -> bool:
        """Update member details"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        member.name = name
        member.phone = phone
        member.membership_type = membership_type
        
        if email is not None:
            member.email = email
        
        if joined_date:
            member.joined_date = datetime.strptime(joined_date, '%Y-%m-%d').date()
        
        self.session.commit()
        return True
    
    def delete_member(self, member_id: str) -> bool:
        """Delete a member and their fees"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        self.session.delete(member)
        self.session.commit()
        return True
    
    def get_member(self, member_id: str) -> Optional[Dict]:
        """Get member details"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return None
        
        return {
            'id': str(member.id),
            'name': member.name,
            'phone': member.phone,
            'email': member.email,
            'photo': member.photo_url,
            'membership_type': member.membership_type,
            'joined_date': member.joined_date.strftime('%Y-%m-%d'),
            'active': member.is_active,
            'is_trial': member.is_trial,
            'trial_end_date': member.trial_end_date.strftime('%Y-%m-%d') if member.trial_end_date else None
        }
    
    def get_all_members(self) -> List[Dict]:
        """Get all members"""
        if not self.gym:
            return []
        
        members = self.session.query(Member).filter_by(gym_id=self.gym.id, is_active=True).all()
        return [
            {
                'id': str(m.id),
                'name': m.name,
                'phone': m.phone,
                'email': m.email,
                'photo': m.photo_url,
                'membership_type': m.membership_type,
                'joined_date': m.joined_date.strftime('%Y-%m-%d'),
                'active': m.is_active,
                'is_trial': m.is_trial,
                'trial_end_date': m.trial_end_date.strftime('%Y-%m-%d') if m.trial_end_date else None
            }
            for m in members
        ]
    
    def search_members(self, query: str) -> List[Dict]:
        """Search members by name or phone"""
        if not self.gym:
            return []
        
        members = self.session.query(Member).filter(
            Member.gym_id == self.gym.id,
            Member.is_active == True,
            (Member.name.ilike(f'%{query}%')) | (Member.phone.ilike(f'%{query}%'))
        ).all()
        
        return [
            {
                'id': str(m.id),
                'name': m.name,
                'phone': m.phone,
                'membership_type': m.membership_type
            }
            for m in members
        ]
    
    def record_fee(self, member_id: str, month: str, amount: float = 0, date: str = None) -> bool:
        """Record a fee payment"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        if not date:
            date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if fee already exists
        existing_fee = self.session.query(Fee).filter_by(member_id=member.id, month=month).first()
        if existing_fee:
            return False
        
        fee = Fee(
            member_id=member.id,
            month=month,
            amount=amount,
            paid_date=datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        )
        
        self.session.add(fee)
        self.session.commit()
        return True
    
    def update_fee(self, member_id: str, month: str, amount: float, date: str) -> bool:
        """Update an existing fee record"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        fee = self.session.query(Fee).filter_by(member_id=member.id, month=month).first()
        if not fee:
            return False
        
        fee.amount = amount
        fee.paid_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        
        self.session.commit()
        return True
    
    def delete_fee(self, member_id: str, month: str) -> bool:
        """Delete a fee record"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        fee = self.session.query(Fee).filter_by(member_id=member.id, month=month).first()
        if not fee:
            return False
        
        self.session.delete(fee)
        self.session.commit()
        return True
    
    def is_fee_paid(self, member_id: str, month: str) -> bool:
        """Check if fee is paid for a month"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        fee = self.session.query(Fee).filter_by(member_id=member.id, month=month).first()
        return fee is not None
    
    def get_payment_status(self, month: str = None) -> Dict:
        """Get payment status for a month"""
        if not month:
            month = datetime.now().strftime('%Y-%m')
        
        if not self.gym:
            return {'paid': [], 'unpaid': []}
        
        all_members = self.session.query(Member).filter_by(gym_id=self.gym.id, is_active=True).all()
        
        paid = []
        unpaid = []
        
        for member in all_members:
            fee = self.session.query(Fee).filter_by(member_id=member.id, month=month).first()
            
            member_data = {
                'id': str(member.id),
                'name': member.name,
                'phone': member.phone,
                'membership_type': member.membership_type
            }
            
            if fee:
                member_data['amount'] = float(fee.amount)
                member_data['date'] = fee.paid_date.strftime('%Y-%m-%d %H:%M:%S')
                paid.append(member_data)
            else:
                unpaid.append(member_data)
        
        return {'paid': paid, 'unpaid': unpaid}
    
    def get_member_fees(self, member_id: str) -> List[Dict]:
        """Get all fees for a member"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return []
        
        fees = self.session.query(Fee).filter_by(member_id=member.id).order_by(Fee.month.desc()).all()
        
        return [
            {
                'month': f.month,
                'amount': float(f.amount),
                'date': f.paid_date.strftime('%Y-%m-%d %H:%M:%S')
            }
            for f in fees
        ]
    
    def get_revenue(self, month: str = None) -> float:
        """Get total revenue for a month"""
        if not month:
            month = datetime.now().strftime('%Y-%m')
        
        if not self.gym:
            return 0.0
        
        # Get all members for this gym
        member_ids = [m.id for m in self.session.query(Member).filter_by(gym_id=self.gym.id).all()]
        
        total = self.session.query(func.sum(Fee.amount)).filter(
            Fee.member_id.in_(member_ids),
            Fee.month == month
        ).scalar()
        
        return float(total) if total else 0.0
    
    def log_attendance(self, member_id: str, emotion: str = None, confidence: float = None) -> bool:
        """Log member attendance"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return False
        
        attendance = Attendance(
            member_id=member.id,
            check_in_time=datetime.now(),
            emotion=emotion,
            confidence=confidence
        )
        
        self.session.add(attendance)
        self.session.commit()
        return True
    
    def get_attendance(self, member_id: str) -> List:
        """Get attendance history for a member"""
        member = self.session.query(Member).filter_by(id=int(member_id), gym_id=self.gym.id).first()
        if not member:
            return []
        
        records = self.session.query(Attendance).filter_by(member_id=member.id).order_by(Attendance.check_in_time.desc()).all()
        
        return [
            {
                'timestamp': r.check_in_time.strftime('%Y-%m-%d %H:%M:%S'),
                'emotion': r.emotion,
                'confidence': float(r.confidence) if r.confidence else None
            }
            for r in records
        ]
    
    # Expense Management
    def add_expense(self, category: str, amount: float, date: str, description: str = '') -> bool:
        """Add an expense record"""
        if not self.gym:
            return False
        
        expense = Expense(
            gym_id=self.gym.id,
            category=category,
            amount=amount,
            date=datetime.strptime(date, '%Y-%m-%d').date(),
            description=description
        )
        
        self.session.add(expense)
        self.session.commit()
        return True
    
    def get_expenses(self, month: str = None) -> list:
        """Get expenses for a month"""
        if not self.gym:
            return []
        
        query = self.session.query(Expense).filter_by(gym_id=self.gym.id)
        
        if month:
            year, month_num = map(int, month.split('-'))
            query = query.filter(
                extract('year', Expense.date) == year,
                extract('month', Expense.date) == month_num
            )
        
        expenses = query.order_by(Expense.date.desc()).all()
        
        return [
            {
                'id': e.id,
                'category': e.category,
                'amount': float(e.amount),
                'date': e.date.strftime('%Y-%m-%d'),
                'description': e.description
            }
            for e in expenses
        ]
    
    def delete_expense(self, expense_id: str) -> bool:
        """Delete an expense"""
        expense = self.session.query(Expense).filter_by(id=expense_id, gym_id=self.gym.id).first()
        if not expense:
            return False
        
        self.session.delete(expense)
        self.session.commit()
        return True
    
    def bulk_import_members(self, filepath: str) -> Tuple[int, int, List[str]]:
        """Import members from Excel/CSV file"""
        import pandas as pd
        
        try:
            if filepath.endswith('.csv'):
                df = pd.read_csv(filepath)
            else:
                df = pd.read_excel(filepath)
            
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    name = str(row.get('Name', '')).strip()
                    phone = str(row.get('Phone', '')).strip()
                    
                    if not name or not phone:
                        errors.append(f"Row {index + 2}: Missing name or phone")
                        error_count += 1
                        continue
                    
                    # Check if member exists
                    existing = self.session.query(Member).filter_by(gym_id=self.gym.id, phone=phone).first()
                    
                    if existing:
                        # Update existing member
                        existing.name = name
                        existing.email = str(row.get('Email', '')).strip()
                        existing.membership_type = str(row.get('Membership Type', 'Gym')).strip()
                        success_count += 1
                    else:
                        # Add new member
                        joined_date = row.get('Joined Date', datetime.now().strftime('%Y-%m-%d'))
                        if pd.isna(joined_date):
                            joined_date = datetime.now().strftime('%Y-%m-%d')
                        
                        member = Member(
                            gym_id=self.gym.id,
                            name=name,
                            phone=phone,
                            email=str(row.get('Email', '')).strip(),
                            membership_type=str(row.get('Membership Type', 'Gym')).strip(),
                            joined_date=datetime.strptime(str(joined_date), '%Y-%m-%d').date()
                        )
                        self.session.add(member)
                        success_count += 1
                
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
            
            self.session.commit()
            return success_count, error_count, errors
        
        except Exception as e:
            return 0, 0, [f"File error: {str(e)}"]
    
    def __del__(self):
        """Close database session"""
        if hasattr(self, 'session'):
            self.session.close()
