"""
from flask import Flask, request, render_template, jsonify, session
from firebase_admin import auth
import os
import logging
import traceback
from login import login_bp
from register import register_bp
from video_processor import process_video

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Register Blueprints for login and register routes
app.register_blueprint(login_bp)
app.register_blueprint(register_bp)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
SUMMARIZED_FOLDER = os.path.abspath('summarized_uploads')
ALLOWED_EXTENSIONS = {'webm', 'mp4'}
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARIZED_FOLDER'] = SUMMARIZED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure the upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARIZED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return jsonify({'error': "No file part"})

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': "No selected file"})

            if file and allowed_file(file.filename):
                # Create a safe filename
                filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                filename = os.path.abspath(filename)
                
                logger.info(f"Saving file to: {filename}")
                file.save(filename)
                logger.info(f"File saved successfully: {filename}")

                user_input = request.form.get('prompt', '')
                logger.info(f"Processing video with prompt: {user_input}")

                # Get user ID from request headers if available
                auth_header = request.headers.get('Authorization')
                user_id = None
                
                if auth_header and auth_header.startswith('Bearer '):
                    try:
                        # Verify the Firebase ID token
                        decoded_token = auth.verify_id_token(auth_header.split('Bearer ')[1])
                        user_id = decoded_token['uid']
                        logger.info(f"Processing for authenticated user: {user_id}")
                    except Exception as e:
                        logger.warning(f"Invalid authentication token: {str(e)}")
                        return jsonify({'error': 'Invalid authentication token'})

                # Process video with user ID if available
                result = process_video(
                    filename, 
                    user_input, 
                    app.config['UPLOAD_FOLDER'], 
                    app.config['SUMMARIZED_FOLDER'],
                    user_id
                )
                
                response = {
                    'output_video_path': result['local_path']
                }
                
                if result.get('firebase_url'):
                    response['firebase_url'] = result['firebase_url']

                return jsonify(response)

        except Exception as e:
            logger.error(f"Error in request processing: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)})

    return render_template('index.html')

@app.route('/videos', methods=['GET'])
def get_user_videos():
    try:
        # Get user ID from request headers
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authentication token provided'}), 401

        try:
            # Verify the Firebase ID token
            decoded_token = auth.verify_id_token(auth_header.split('Bearer ')[1])
            user_id = decoded_token['uid']
        except Exception as e:
            logger.warning(f"Invalid authentication token: {str(e)}")
            return jsonify({'error': 'Invalid authentication token'}), 401

        # Get user's video folder path
        user_folder = os.path.join(app.config['SUMMARIZED_FOLDER'], user_id)
        
        # If folder doesn't exist, return empty list
        if not os.path.exists(user_folder):
            return jsonify({'videos': []})

        # Get list of videos in user's folder
        videos = []
        for filename in os.listdir(user_folder):
            if filename.endswith(('.mp4', '.webm')):
                video_path = os.path.join(user_folder, filename)
                videos.append({
                    'filename': filename,
                    'path': video_path,
                    'created': os.path.getctime(video_path)
                })

        # Sort videos by creation time, newest first
        videos.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'videos': videos})

    except Exception as e:
        logger.error(f"Error getting user videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)"""
from flask import Flask, request, render_template, jsonify, session
from flask_cors import CORS  # Added CORS import
from firebase_admin import auth
import os
import logging
import traceback
from login import login_bp
from register import register_bp
from video_processor import process_video

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
# Enable CORS with specific configuration
CORS(app, resources={
    r"/*": {
        "origins": "http://localhost:5000",  # Frontend origin
        "allow_headers": ["Authorization", "Content-Type"]
    }
})

# Register Blueprints for login and register routes
app.register_blueprint(login_bp)
app.register_blueprint(register_bp)

# Configuration
UPLOAD_FOLDER = os.path.abspath('uploads')
SUMMARIZED_FOLDER = os.path.abspath('summarized_uploads')
ALLOWED_EXTENSIONS = {'webm', 'mp4'}
MAX_CONTENT_LENGTH = 1024 * 1024 * 1024  # 1GB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUMMARIZED_FOLDER'] = SUMMARIZED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure the upload directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUMMARIZED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            if 'file' not in request.files:
                return jsonify({'error': "No file part"})

            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': "No selected file"})

            if file and allowed_file(file.filename):
                # Create a safe filename
                filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                filename = os.path.abspath(filename)
                
                logger.info(f"Saving file to: {filename}")
                file.save(filename)
                logger.info(f"File saved successfully: {filename}")

                user_input = request.form.get('prompt', '')
                logger.info(f"Processing video with prompt: {user_input}")

                # Get user ID from request headers if available
                auth_header = request.headers.get('Authorization')
                user_id = None
                
                if auth_header and auth_header.startswith('Bearer '):
                    try:
                        # Verify the Firebase ID token
                        decoded_token = auth.verify_id_token(auth_header.split('Bearer ')[1])
                        user_id = decoded_token['uid']
                        logger.info(f"Processing for authenticated user: {user_id}")
                    except Exception as e:
                        logger.warning(f"Invalid authentication token: {str(e)}")
                        return jsonify({'error': 'Invalid authentication token'})

                # Process video with user ID if available
                result = process_video(
                    filename, 
                    user_input, 
                    app.config['UPLOAD_FOLDER'], 
                    app.config['SUMMARIZED_FOLDER'],
                    user_id
                )
                
                response = {
                    'output_video_path': result['local_path']
                }
                
                if result.get('firebase_url'):
                    response['firebase_url'] = result['firebase_url']

                return jsonify(response)

        except Exception as e:
            logger.error(f"Error in request processing: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({'error': str(e)})

    return render_template('index.html')

@app.route('/videos', methods=['GET'])
def get_user_videos():
    try:
        # Get user ID from request headers
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No authentication token provided'}), 401

        try:
            # Verify the Firebase ID token
            decoded_token = auth.verify_id_token(auth_header.split('Bearer ')[1])
            user_id = decoded_token['uid']
        except Exception as e:
            logger.warning(f"Invalid authentication token: {str(e)}")
            return jsonify({'error': 'Invalid authentication token'}), 401

        # Get user's video folder path
        user_folder = os.path.join(app.config['SUMMARIZED_FOLDER'], user_id)
        
        # If folder doesn't exist, return empty list
        if not os.path.exists(user_folder):
            return jsonify({'videos': []})

        # Get list of videos in user's folder
        videos = []
        for filename in os.listdir(user_folder):
            if filename.endswith(('.mp4', '.webm')):
                video_path = os.path.join(user_folder, filename)
                videos.append({
                    'filename': filename,
                    'path': video_path,
                    'created': os.path.getctime(video_path)
                })

        # Sort videos by creation time, newest first
        videos.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'videos': videos})

    except Exception as e:
        logger.error(f"Error getting user videos: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)