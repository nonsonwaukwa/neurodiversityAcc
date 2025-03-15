from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.tasks import get_task_service
import json

# Create blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
def get_users():
    """Get all users"""
    try:
        # Extract query parameters
        user_type = request.args.get('type')  # 'AI' or 'Human'
        
        # Get users
        users = User.get_all(user_type)
        
        # Convert to dictionaries
        users_data = [user.to_dict() for user in users]
        
        return jsonify({"users": users_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Get a specific user"""
    try:
        user = User.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        return jsonify({"user": user.to_dict()}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    """Get tasks for a specific user"""
    try:
        # Extract query parameters
        status = request.args.get('status')
        limit = request.args.get('limit')
        
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        
        # Get tasks
        task_service = get_task_service()
        tasks = task_service.get_user_tasks(user_id, status, limit)
        
        # Convert to dictionaries
        tasks_data = [task.to_dict() for task in tasks]
        
        return jsonify({"tasks": tasks_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>/checkins', methods=['GET'])
def get_user_checkins(user_id):
    """Get check-ins for a specific user"""
    try:
        # Extract query parameters
        checkin_type = request.args.get('type')
        limit = request.args.get('limit')
        
        if limit:
            try:
                limit = int(limit)
            except ValueError:
                limit = None
        
        # Get check-ins
        checkins = CheckIn.get_for_user(user_id, checkin_type, limit)
        
        # Convert to dictionaries
        checkins_data = [checkin.to_dict() for checkin in checkins]
        
        return jsonify({"checkins": checkins_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    try:
        # This is a simplified implementation
        # In a real app, you would probably want pagination and filtering
        
        # Get all users
        users = User.get_all()
        
        all_tasks = []
        for user in users:
            # Get tasks for each user
            tasks = Task.get_for_user(user.user_id)
            all_tasks.extend(tasks)
        
        # Convert to dictionaries
        tasks_data = [task.to_dict() for task in all_tasks]
        
        return jsonify({"tasks": tasks_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/checkins', methods=['GET'])
def get_checkins():
    """Get all check-ins"""
    try:
        # This is a simplified implementation
        # In a real app, you would probably want pagination and filtering
        
        # Get all users
        users = User.get_all()
        
        all_checkins = []
        for user in users:
            # Get check-ins for each user
            checkins = CheckIn.get_for_user(user.user_id)
            all_checkins.extend(checkins)
        
        # Convert to dictionaries
        checkins_data = [checkin.to_dict() for checkin in all_checkins]
        
        return jsonify({"checkins": checkins_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/analytics', methods=['GET'])
def get_analytics():
    """Get analytics data"""
    try:
        # Get all users
        users = User.get_all()
        
        # Initialize counters
        total_users = len(users)
        active_users = 0
        ai_users = 0
        human_users = 0
        
        total_tasks = 0
        completed_tasks = 0
        stuck_tasks = 0
        
        total_checkins = 0
        avg_sentiment = 0
        
        # Count users by type
        for user in users:
            if user.type == 'AI':
                ai_users += 1
            else:
                human_users += 1
        
        # Get all tasks
        all_tasks = []
        for user in users:
            # Get tasks for each user
            tasks = Task.get_for_user(user.user_id)
            all_tasks.extend(tasks)
        
        # Count tasks by status
        total_tasks = len(all_tasks)
        completed_tasks = sum(1 for task in all_tasks if task.status == Task.STATUS_DONE)
        stuck_tasks = sum(1 for task in all_tasks if task.status == Task.STATUS_STUCK)
        
        # Calculate task completion rate
        completion_rate = 0
        if total_tasks > 0:
            completion_rate = (completed_tasks / total_tasks) * 100
        
        # Get all check-ins
        all_checkins = []
        for user in users:
            # Get check-ins for each user
            checkins = CheckIn.get_for_user(user.user_id)
            all_checkins.extend(checkins)
        
        # Calculate average sentiment
        total_checkins = len(all_checkins)
        sentiment_scores = [checkin.sentiment_score for checkin in all_checkins if checkin.sentiment_score is not None]
        
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
        
        # Prepare response
        analytics_data = {
            "users": {
                "total": total_users,
                "ai": ai_users,
                "human": human_users
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "stuck": stuck_tasks,
                "completion_rate": completion_rate
            },
            "checkins": {
                "total": total_checkins,
                "avg_sentiment": avg_sentiment
            }
        }
        
        return jsonify({"analytics": analytics_data}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users', methods=['POST'])
def create_user():
    """Create a new user"""
    try:
        data = request.json
        
        # Validate required fields
        if not all(key in data for key in ['user_id', 'name']):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Check if user already exists
        existing_user = User.get(data['user_id'])
        if existing_user:
            return jsonify({"error": "User already exists"}), 409
        
        # Create user
        user_type = data.get('type', 'Human')
        user = User.create(data['user_id'], data['name'], user_type)
        
        return jsonify({"user": user.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/users/<user_id>/tasks', methods=['POST'])
def create_user_task(user_id):
    """Create a new task for a user"""
    try:
        data = request.json
        
        # Validate required fields
        if 'description' not in data:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Check if user exists
        user = User.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Create task
        task_service = get_task_service()
        category = data.get('category', Task.CATEGORY_OTHER)
        task = task_service.create_task(user_id, data['description'], category)
        
        return jsonify({"task": task.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500 