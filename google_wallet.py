"""
Google Wallet Pass Generator for Gym Manager
Simplified implementation for creating digital membership cards
"""

import os
import json
from google.auth.transport.requests import AuthorizedSession
from google.oauth2.service_account import Credentials
from google.auth import jwt, crypt
import datetime


class GymWalletPass:
    """Create Google Wallet passes for gym members"""
    
    def __init__(self):
        """Initialize with service account credentials"""
        # Load credentials from environment variable
        key_file_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if key_file_path and os.path.exists(key_file_path):
            self.credentials = Credentials.from_service_account_file(
                key_file_path,
                scopes=['https://www.googleapis.com/auth/wallet_object.issuer']
            )
            self.http_client = AuthorizedSession(self.credentials)
            self.issuer_id = os.getenv('WALLET_ISSUER_ID')
        else:
            self.credentials = None
            self.http_client = None
            self.issuer_id = None
    
    def is_configured(self):
        """Check if wallet is properly configured"""
        return self.credentials is not None and self.issuer_id is not None
    
    def create_class(self, gym_name, gym_logo_url=None):
        """Create or update a loyalty class for the gym"""
        if not self.is_configured():
            return None
        
        class_id = f"{self.issuer_id}.{gym_name.replace(' ', '_').lower()}_membership"
        
        # Define the loyalty class
        loyalty_class = {
            'id': class_id,
            'issuerName': gym_name,
            'programName': f'{gym_name} Membership',
            'programLogo': {
                'sourceUri': {
                    'uri': gym_logo_url or 'https://via.placeholder.com/300x100'
                }
            },
            'reviewStatus': 'UNDER_REVIEW',
            'hexBackgroundColor': '#4285f4'
        }
        
        # Try to create the class
        try:
            response = self.http_client.post(
                'https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass',
                json=loyalty_class
            )
            
            if response.status_code == 200:
                return class_id
            elif response.status_code == 409:  # Already exists
                return class_id
            else:
                print(f"Error creating class: {response.text}")
                return None
        except Exception as e:
            print(f"Exception creating class: {str(e)}")
            return None
    
    def create_pass_object(self, member_id, member_name, member_phone, 
                          expiry_date=None, gym_name="Gym Manager"):
        """Create a wallet pass object for a member"""
        if not self.is_configured():
            return None
        
        # Generate unique object ID
        object_id = f"{self.issuer_id}.{member_id}"
        class_id = f"{self.issuer_id}.{gym_name.replace(' ', '_').lower()}_membership"
        
        # Create pass object
        loyalty_object = {
            'id': object_id,
            'classId': class_id,
            'state': 'ACTIVE',
            'accountId': member_id,
            'accountName': member_name,
            'loyaltyPoints': {
                'label': 'Member ID',
                'balance': {
                    'string': member_id
                }
            },
            'textModulesData': [
                {
                    'header': 'Contact',
                    'body': member_phone
                }
            ],
            'barcode': {
                'type': 'QR_CODE',
                'value': member_id
            }
        }
        
        # Add expiry if provided
        if expiry_date:
            loyalty_object['validTimeInterval'] = {
                'end': {
                    'date': expiry_date
                }
            }
        
        try:
            response = self.http_client.post(
                'https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject',
                json=loyalty_object
            )
            
            if response.status_code in [200, 409]:
                return object_id
            else:
                print(f"Error creating object: {response.text}")
                return None
        except Exception as e:
            print(f"Exception creating object: {str(e)}")
            return None
    
    def create_jwt_save_url(self, member_id, member_name, member_phone, 
                           gym_name="Gym Manager"):
        """Create a JWT token for 'Add to Google Wallet' link"""
        if not self.is_configured():
            return None
        
        object_id = f"{self.issuer_id}.{member_id}"
        class_id = f"{self.issuer_id}.{gym_name.replace(' ', '_').lower()}_membership"
        
        # Claims for JWT
        claims = {
            'iss': self.credentials.service_account_email,
            'aud': 'google',
            'origins': [],
            'typ': 'savetowallet',
            'payload': {
                'loyaltyObjects': [{
                    'id': object_id,
                    'classId': class_id,
                    'state': 'ACTIVE',
                    'accountId': member_id,
                    'accountName': member_name,
                    'loyaltyPoints': {
                        'label': 'Member ID',
                        'balance': {
                            'string': member_id
                        }
                    },
                    'textModulesData': [{
                        'header': 'Contact',
                        'body': member_phone
                    }],
                    'barcode': {
                        'type': 'QR_CODE',
                        'value': member_id
                    }
                }]
            }
        }
        
        # Create signed JWT
        signer = crypt.RSASigner.from_service_account_file(
            os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        )
        token = jwt.encode(signer, claims)
        
        # Return the save URL
        return f"https://pay.google.com/gp/v/save/{token}"
