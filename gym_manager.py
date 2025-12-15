import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class GymManager:
    def __init__(self, data_file):
        """Initialize with a specific user's data file"""
        self.data_file = data_file
        self.data = self.load_data()
    
    def load_data(self) -> Dict:
        """Load data from JSON file or create new structure"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_empty_data()
        return self._create_empty_data()
    
    def _create_empty_data(self) -> Dict:
        """Create empty data structure"""
        return {
            # 'admin' key is no longer used for auth, but kept structure if needed or ignored
            'admin': None, 
            'members': {},
            'fees': {},
            'expenses': {},  # NEW: Track gym expenses
            'next_member_id': 1,
            'gym_details': {
                'name': 'Gym Manager',
                'logo': None,
                'currency': '$'
            }
        }
    
    def get_gym_details(self) -> Dict:
        """Get gym name and logo"""
        # Ensure key exists for older data files
        if 'gym_details' not in self.data:
            self.data['gym_details'] = {'name': 'Gym Manager', 'logo': None, 'currency': '$'}
            self.save_data()
        # Ensure currency exists
        if 'currency' not in self.data['gym_details']:
            self.data['gym_details']['currency'] = '$'
            self.save_data()
        return self.data['gym_details']

    def update_gym_details(self, name: str, logo_path: Optional[str] = None, currency: str = '$') -> bool:
        """Update gym name, logo, and currency"""
        if 'gym_details' not in self.data:
            self.data['gym_details'] = {}
        
        self.data['gym_details']['name'] = name
        self.data['gym_details']['currency'] = currency
        if logo_path:
            self.data['gym_details']['logo'] = logo_path
            
        self.save_data()
        return True
    
    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def reset_data(self):
        """Reset everything (Factory Reset) for this user"""
        self.data = self._create_empty_data()
        self.save_data()
        return True
    
    # Removed signup_admin, login_admin, has_admin - handled by AuthManager now
    
    def add_member(self, name: str, phone: str, photo: str = None, membership_type: str = 'Gym', joined_date: str = None, is_trial: bool = False, email: str = None) -> int:
        """Add a new member"""
        member_id = str(self.data['next_member_id'])
        if not joined_date:
            joined_date = datetime.now().strftime('%Y-%m-%d')
            
        trial_end = None
        if is_trial:
            trial_end = (datetime.strptime(joined_date, '%Y-%m-%d') + timedelta(days=3)).strftime('%Y-%m-%d')
            
        self.data['members'][member_id] = {
            'id': member_id,
            'name': name,
            'phone': phone,
            'email': email or '',
            'photo': photo,
            'joined_date': joined_date,
            'active': True,
            'membership_type': membership_type,
            'is_trial': is_trial,
            'trial_end_date': trial_end
        }
        self.data['next_member_id'] += 1
        self.save_data()
        return int(member_id)

    def update_member(self, member_id: str, name: str, phone: str, membership_type: str, joined_date: Optional[str] = None, email: str = None) -> bool:
        """Update member details"""
        if member_id not in self.data['members']:
            return False
        
        self.data['members'][member_id]['name'] = name
        self.data['members'][member_id]['phone'] = phone
        self.data['members'][member_id]['membership_type'] = membership_type
        
        if email is not None:
            self.data['members'][member_id]['email'] = email
        
        if joined_date:
            self.data['members'][member_id]['joined_date'] = joined_date
            
        self.save_data()
        return True

    def delete_member(self, member_id: str) -> bool:
        """Delete a member and their fees"""
        if member_id not in self.data['members']:
            return False
        
        del self.data['members'][member_id]
        if member_id in self.data['fees']:
            del self.data['fees'][member_id]
            
        self.save_data()
        return True
    
    # Expense Management Methods
    def add_expense(self, category: str, amount: float, date: str, description: str = '') -> bool:
        """Add an expense record"""
        if 'expenses' not in self.data:
            self.data['expenses'] = {}
        
        expense_id = f"EXP{len(self.data['expenses']) + 1:04d}"
        self.data['expenses'][expense_id] = {
            'id': expense_id,
            'category': category,
            'amount': amount,
            'date': date,
            'description': description
        }
        self.save_data()
        return True
    
    def get_expenses(self, month: str = None) -> list:
        """Get all expenses or filter by month"""
        if 'expenses' not in self.data:
            return []
        
        expenses = list(self.data['expenses'].values())
        
        if month:
            expenses = [e for e in expenses if e['date'].startswith(month)]
        
        # Sort by date descending
        expenses.sort(key=lambda x: x['date'], reverse=True)
        return expenses
    
    def delete_expense(self, expense_id: str) -> bool:
        """Delete an expense"""
        if 'expenses' not in self.data or expense_id not in self.data['expenses']:
            return False
        
        del self.data['expenses'][expense_id]
        self.save_data()
        return True
    
    def calculate_profit_loss(self, month: str) -> Dict:
        """Calculate P&L for a given month"""
        # Get revenue
        status = self.get_payment_status(month)
        revenue = sum(m.get('amount', 0) for m in status['paid'])
        
        # Get expenses
        expenses = self.get_expenses(month)
        total_expenses = sum(e['amount'] for e in expenses)
        
        # Calculate profit
        net_profit = revenue - total_expenses
        profit_margin = (net_profit / revenue * 100) if revenue > 0 else 0
        
        return {
            'revenue': revenue,
            'expenses': total_expenses,
            'net_profit': net_profit,
            'profit_margin': round(profit_margin, 2)
        }
    
    def get_all_members(self) -> List[Dict]:
        """Get all members as a list"""
        return list(self.data['members'].values())
    
    def get_member(self, member_id: str) -> Optional[Dict]:
        """Get a specific member"""
        return self.data['members'].get(member_id)
    
    def pay_fee(self, member_id: str, month: str, amount: float = 0, paid_date: str = None, notes: str = None) -> bool:
        """Record fee payment for a member"""
        if member_id not in self.data['members']:
            return False
        
        if member_id not in self.data['fees']:
            self.data['fees'][member_id] = {}
        
        if not paid_date:
            paid_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
        self.data['fees'][member_id][month] = {
            'amount': amount,
            'paid_date': paid_date,
            'notes': notes or ''
        }
        self.save_data()
        return True
    
    def delete_fee(self, member_id: str, month: str) -> bool:
        """Delete a fee record"""
        if member_id not in self.data['fees'] or month not in self.data['fees'][member_id]:
            return False
            
        del self.data['fees'][member_id][month]
        self.save_data()
        return True

    def update_fee(self, member_id: str, month: str, amount: float, date: str, notes: str = None) -> bool:
        """Update a fee record"""
        if member_id not in self.data['fees'] or month not in self.data['fees'][member_id]:
            return False
            
        self.data['fees'][member_id][month]['amount'] = amount
        self.data['fees'][member_id][month]['paid_date'] = date
        if notes is not None:
            self.data['fees'][member_id][month]['notes'] = notes
        
        self.save_data()
        return True

    def is_fee_paid(self, member_id: str, month: str) -> bool:
        """Check if fee is paid for a specific month"""
        if member_id not in self.data['fees']:
            return False
        return month in self.data['fees'][member_id]

    def log_attendance(self, member_id: str) -> bool:
        """Log a visit for the member"""
        if member_id not in self.data['members']:
            return False
        
        if 'attendance' not in self.data:
            self.data['attendance'] = {}
            
        if member_id not in self.data['attendance']:
            self.data['attendance'][member_id] = []
            
        # Add timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.data['attendance'][member_id].append(timestamp)
        self.save_data()
        return True

    def get_attendance(self, member_id: str) -> List[str]:
        """Get attendance history for a member"""
        if 'attendance' not in self.data:
            return []
        # Return reversed list (newest first)
        return self.data['attendance'].get(member_id, [])[::-1]
    
    # --- Class Scheduling Methods ---
    def add_class(self, name: str, day: str, time: str, instructor: str, capacity: int) -> str:
        """Add a new fitness class"""
        if 'classes' not in self.data:
            self.data['classes'] = {}
            
        class_id = str(len(self.data['classes']) + 1)
        self.data['classes'][class_id] = {
            'id': class_id,
            'name': name,
            'day': day, # e.g., "Monday"
            'time': time, # e.g., "17:00"
            'instructor': instructor,
            'capacity': int(capacity),
            'attendees': []
        }
        self.save_data()
        return class_id
        
    def book_class(self, member_id: str, class_id: str) -> bool:
        """Book a member into a class"""
        if 'classes' not in self.data or class_id not in self.data['classes']:
            return False
            
        cls = self.data['classes'][class_id]
        if member_id in cls['attendees']:
            return True # Already booked
            
        if len(cls['attendees']) >= cls['capacity']:
            return False # Full
            
        cls['attendees'].append(member_id)
        self.save_data()
        return True
        
    def get_classes(self) -> List[Dict]:
        """Get all classes"""
        if 'classes' not in self.data:
            return []
        return list(self.data['classes'].values())

    def get_payment_status(self, month: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get paid/unpaid members for a specific month"""
        if month is None:
            month = datetime.now().strftime('%Y-%m')
        
        paid = []
        unpaid = []
        
        for member_id, member in self.data['members'].items():
            if self.is_fee_paid(member_id, month):
                fee_info = self.data['fees'][member_id][month]
                member_copy = member.copy()
                member_copy['last_paid'] = fee_info['paid_date']
                member_copy['amount'] = fee_info['amount']
                paid.append(member_copy)
            else:
                unpaid.append(member)
        
        return {'paid': paid, 'unpaid': unpaid}
    
    def get_member_fee_history(self, member_id: str) -> List[Dict]:
        """Get fee payment history for a member"""
        if member_id not in self.data['fees']:
            return []
        
        history = []
        for month, info in self.data['fees'][member_id].items():
            history.append({
                'month': month,
                'amount': info['amount'],
                'paid_date': info['paid_date'],
                'notes': info.get('notes', '')
            })
        return sorted(history, key=lambda x: x['month'], reverse=True)
    
    def get_payment_history(self, member_id: str) -> List[Dict]:
        """Alias for get_member_fee_history for compatibility"""
        return self.get_member_fee_history(member_id)
