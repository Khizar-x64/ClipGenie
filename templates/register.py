from flask import Blueprint, request, jsonify
from firebase_admin import auth
from firebase_init import initialize_firebase

# Initialize Firebase
initialize_firebase()

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Create a new user in Firebase
        user = auth.create_user(
            email=email,
            password=password
        )

        return jsonify({
            'message': 'User registered successfully',
            'user': {
                'uid': user.uid,
                'email': user.email
            }
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500