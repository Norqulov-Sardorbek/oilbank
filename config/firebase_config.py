# firebase_config.py
import firebase_admin
from firebase_admin import credentials
import os

def initialize_firebase():
    if not firebase_admin._apps:  # Check if Firebase is already initialized
        cred = credentials.Certificate(os.path.join(os.path.dirname(__file__), 'credentials', 'serviceAccountKey.json'))
        firebase_admin.initialize_app(cred)