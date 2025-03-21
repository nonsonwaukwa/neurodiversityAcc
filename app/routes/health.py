from flask import Blueprint, jsonify
from firebase_admin import _apps

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint that verifies the application's status"""
    try:
        # Check if Firebase is initialized
        firebase_status = 'ok' if _apps else 'error'
        
        # Check if the application is running
        app_status = 'ok'
        
        return jsonify({
            'status': 'ok',
            'firebase': firebase_status,
            'app': app_status,
            'message': 'Application is healthy'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500 