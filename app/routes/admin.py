from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.tasks import get_task_service
from app.services.analytics import get_analytics_service
from app.services.enhanced_analytics import EnhancedAnalyticsService
from app.services.conversation_analytics import ConversationAnalyticsService
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
        # Get services
        analytics_service = get_analytics_service()
        enhanced_analytics = EnhancedAnalyticsService()
        conversation_analytics = ConversationAnalyticsService()
        
        # Get query parameters
        user_id = request.args.get('user_id')
        days = int(request.args.get('days', 30))
        
        # Get all users
        users = User.get_all()
        total_users = len(users)
        
        if user_id:
            # Get per-user analytics
            user = User.get(user_id)
            if not user:
                return jsonify({"error": "User not found"}), 404
                
            # Get user-specific metrics
            engagement_metrics = enhanced_analytics.track_user_engagement(user_id)
            theme_stats = conversation_analytics.get_user_theme_statistics(user_id, days)
            avg_response_time = enhanced_analytics.get_average_response_time(user_id, days)
            
            # Get user's tasks
            user_tasks = Task.get_for_user(user_id)
            completed_tasks = sum(1 for task in user_tasks if task.status == Task.STATUS_DONE)
            total_tasks = len(user_tasks)
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get user's check-ins
            user_checkins = CheckIn.get_for_user(user_id)
            sentiment_scores = [c.sentiment_score for c in user_checkins if c.sentiment_score is not None]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            analytics_data = {
                "user_metrics": {
                    "engagement_score": engagement_metrics['engagement_score'],
                    "days_active": engagement_metrics['days_active'],
                    "total_checkins": engagement_metrics['total_checkins'],
                    "completed_tasks": completed_tasks,
                    "task_completion_rate": completion_rate,
                    "avg_sentiment": avg_sentiment,
                    "avg_response_time_seconds": avg_response_time,
                    "streak_count": user.streak_count
                },
                "conversation_themes": {
                    "common_struggles": theme_stats['common_struggles'],
                    "common_tasks": theme_stats['common_tasks'],
                    "total_messages": theme_stats['total_messages']
                }
            }
        else:
            # Get global analytics
            # Initialize counters
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
                tasks = Task.get_for_user(user.user_id)
                all_tasks.extend(tasks)
            
            # Count tasks by status
            total_tasks = len(all_tasks)
            completed_tasks = sum(1 for task in all_tasks if task.status == Task.STATUS_DONE)
            stuck_tasks = sum(1 for task in all_tasks if task.status == Task.STATUS_STUCK)
            
            # Calculate task completion rate
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Get all check-ins
            all_checkins = []
            for user in users:
                checkins = CheckIn.get_for_user(user.user_id)
                all_checkins.extend(checkins)
            
            # Calculate average sentiment
            total_checkins = len(all_checkins)
            sentiment_scores = [checkin.sentiment_score for checkin in all_checkins if checkin.sentiment_score is not None]
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
            
            # Get enhanced analytics
            streak_stats = enhanced_analytics.get_streak_statistics()
            dropout_stats = enhanced_analytics.get_dropout_statistics(days)
            avg_response_time = enhanced_analytics.get_average_response_time(days=days)
            
            # Get conversation theme analytics
            theme_stats = conversation_analytics.get_global_theme_statistics(days)
            
            analytics_data = {
                "global_metrics": {
                    "users": {
                        "total": total_users,
                        "ai": ai_users,
                        "human": human_users,
                        "at_risk": dropout_stats['at_risk_users'],
                        "dropout_rate": dropout_stats['dropout_rate']
                    },
                    "tasks": {
                        "total": total_tasks,
                        "completed": completed_tasks,
                        "stuck": stuck_tasks,
                        "completion_rate": completion_rate
                    },
                    "checkins": {
                        "total": total_checkins,
                        "avg_sentiment": avg_sentiment,
                        "avg_response_time_seconds": avg_response_time
                    },
                    "streaks": {
                        "average": streak_stats['average_streak'],
                        "max": streak_stats['max_streak'],
                        "active": streak_stats['active_streaks']
                    }
                },
                "conversation_themes": {
                    "global_struggles": theme_stats['global_struggles'],
                    "global_tasks": theme_stats['global_tasks'],
                    "total_messages": theme_stats['total_messages'],
                    "unique_users": theme_stats['unique_users'],
                    "avg_struggles_per_user": theme_stats['avg_struggles_per_user'],
                    "avg_tasks_per_user": theme_stats['avg_tasks_per_user'],
                    "theme_distribution": theme_stats['theme_distribution']
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
        # Validate that the user exists
        user = User.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get task data from request
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400
        
        description = data.get('description')
        if not description:
            return jsonify({"error": "Task description is required"}), 400
        
        # Create the task
        task = Task.create(user_id, description)
        
        return jsonify({"task": task.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500 