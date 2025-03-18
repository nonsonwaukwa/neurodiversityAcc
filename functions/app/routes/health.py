from flask import Blueprint, jsonify

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Railway monitoring"""
    return jsonify({
        "status": "healthy",
        "message": "Neurodiversity Accountability System is running"
    }), 200 