import firebase_admin
from firebase_admin import credentials, storage

def initialize_firebase():
    try:
        app = firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate('firebase-admin-sdk.json')
        app = firebase_admin.initialize_app(cred, {
            'storageBucket': 'clip-f2a05.appspot.com'  # Replace with your bucket name
        })
    
    return app