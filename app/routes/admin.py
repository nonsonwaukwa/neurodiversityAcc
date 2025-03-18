from flask import Blueprint, request, jsonify, render_template, current_app, session, redirect, url_for
from app.models.user import User
from app.models.task import Task
from app.models.checkin import CheckIn
from app.services.tasks import get_task_service
from app.services.analytics import get_analytics_service, calculate_metrics
from app.services.enhanced_analytics import EnhancedAnalyticsService
from app.services.conversation_analytics import ConversationAnalyticsService
from datetime import datetime, timedelta
from app.auth.middleware import admin_required, verify_firebase_token
import json
import firebase_admin
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/login', methods=['GET'])
def login():
    """Show login page"""
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard'))
    
    # Get Firebase config from environment
    firebase_config = {
        'api_key': current_app.config['FIREBASE_API_KEY'],
        'auth_domain': current_app.config['FIREBASE_AUTH_DOMAIN'],
        'project_id': current_app.config['FIREBASE_PROJECT_ID'],
        'storage_bucket': current_app.config['FIREBASE_STORAGE_BUCKET'],
        'messaging_sender_id': current_app.config['FIREBASE_MESSAGING_SENDER_ID'],
        'app_id': current_app.config['FIREBASE_APP_ID']
    }
    
    return render_template('admin/login.html', firebase_config=firebase_config)

@admin_bp.route('/auth/login', methods=['POST'])
def auth_login():
    """Handle login authentication"""
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            logger.warning("No token provided in request")
            return jsonify({'error': 'No token provided'}), 400
        
        # Verify the token and get user info
        user_data = verify_firebase_token(data['token'])
        
        # Clear any existing session
        session.clear()
        
        # Set session data
        session.permanent = True  # Use permanent session
        session['user_id'] = user_data['uid']
        session['email'] = user_data['email']
        session['display_name'] = user_data.get('display_name')
        session['is_admin'] = True
        
        logger.info(f"Admin user logged in successfully: {user_data['email']}")
        
        return jsonify({
            'success': True,
            'redirect': url_for('admin.dashboard')
        }), 200
        
    except ValueError as e:
        logger.warning(f"Login validation error: {str(e)}")
        session.clear()
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        session.clear()
        return jsonify({'error': 'Authentication failed. Please try again.'}), 500

@admin_bp.route('/logout')
def logout():
    """Handle logout"""
    session.clear()
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Show admin dashboard"""
    # Get Firestore client
    db = firestore.client()
    
    # Calculate time ranges
    now = datetime.utcnow()
    last_30_days = now - timedelta(days=30)
    
    # Get all users
    ai_users = []
    traditional_users = []
    users_ref = db.collection('users').stream()
    for user_doc in users_ref:
        user_data = user_doc.to_dict()
        if user_data.get('tracking_type') == User.TRACKING_TYPE_AI:
            ai_users.append(user_data)
        else:
            traditional_users.append(user_data)
    
    # Calculate metrics for AI users
    ai_metrics = {
        'total_users': len(ai_users),
        'task_completion_rate': calculate_task_completion_rate(db, ai_users, last_30_days),
        'engagement_rate': calculate_engagement_rate(db, ai_users, last_30_days),
        'avg_sentiment': calculate_average_sentiment(db, ai_users, last_30_days)
    }
    
    # Calculate metrics for traditional users
    human_metrics = {
        'total_users': len(traditional_users),
        'task_completion_rate': calculate_task_completion_rate(db, traditional_users, last_30_days),
        'engagement_rate': calculate_engagement_rate(db, traditional_users, last_30_days),
        'avg_sentiment': calculate_average_sentiment(db, traditional_users, last_30_days)
    }
    
    # Get recent activity
    recent_activity = get_recent_activity(db, limit=10)
    
    return render_template('admin/dashboard.html',
                         ai_metrics=ai_metrics,
                         human_metrics=human_metrics,
                         recent_activity=recent_activity)

def calculate_task_completion_rate(db, users, since_date):
    """Calculate the percentage of tasks completed on time."""
    total_tasks = 0
    completed_tasks = 0
    
    for user in users:
        # First get all tasks for the user
        tasks_ref = (db.collection('tasks')
                    .where('user_id', '==', user['user_id'])
                    .order_by('created_at')
                    .start_at({'created_at': since_date})
                    .stream())
        
        for task in tasks_ref:
            task_data = task.to_dict()
            total_tasks += 1
            if task_data.get('status') == 'completed' and task_data.get('completed_at'):
                if task_data['completed_at'] <= task_data.get('scheduled_date', task_data['completed_at']):
                    completed_tasks += 1
    
    return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

def calculate_engagement_rate(db, users, since_date):
    """Calculate the percentage of users who interacted in the last 30 days."""
    active_users = 0
    
    for user in users:
        # Check for any task updates, messages, or interactions
        interactions = (
            db.collection('tasks')
            .where('user_id', '==', user['user_id'])
            .order_by('updated_at')
            .start_at({'updated_at': since_date})
            .limit(1)
            .stream()
        )
        
        if len(list(interactions)) > 0:
            active_users += 1
            continue
        
        messages = (
            db.collection('messages')
            .where('user_id', '==', user['user_id'])
            .order_by('timestamp')
            .start_at({'timestamp': since_date})
            .limit(1)
            .stream()
        )
        
        if len(list(messages)) > 0:
            active_users += 1
    
    return (active_users / len(users) * 100) if users else 0

def calculate_average_sentiment(db, users, since_date):
    """Calculate average sentiment score from user messages."""
    total_sentiment = 0
    message_count = 0
    
    for user in users:
        # First get messages by timestamp
        messages = (
            db.collection('messages')
            .where('user_id', '==', user['user_id'])
            .order_by('timestamp')
            .start_at({'timestamp': since_date})
            .stream()
        )
        
        # Then filter sentiment scores in memory
        for msg in messages:
            msg_data = msg.to_dict()
            sentiment_score = msg_data.get('sentiment_score', 0)
            if sentiment_score > 0:
                total_sentiment += sentiment_score
                message_count += 1
    
    return (total_sentiment / message_count) if message_count > 0 else 0

def get_recent_activity(db, limit=10):
    """Get recent user activities across the system."""
    activities = []
    
    # Get recent task updates
    tasks = (
        db.collection('tasks')
        .order_by('updated_at', direction=firestore.Query.DESCENDING)
        .limit(limit)
        .stream()
    )
    
    for task in tasks:
        task_data = task.to_dict()
        user = db.collection('users').document(task_data['user_id']).get()
        user_data = user.to_dict()
        
        activities.append({
            'timestamp': task_data['updated_at'],
            'user_name': user_data.get('name', 'Unknown User'),
            'user_id': task_data['user_id'],
            'type': 'AI' if user_data.get('tracking_type') == User.TRACKING_TYPE_AI else 'Traditional',
            'action': f"Updated task: {task_data.get('status', 'unknown status')}"
        })
    
    # Sort activities by timestamp
    activities.sort(key=lambda x: x['timestamp'], reverse=True)
    return activities[:limit]

@admin_bp.route('/users')
@admin_required
def users():
    """Show users page or return users JSON based on Accept header"""
    # Get Firestore client
    db = firestore.client()
    
    # Extract query parameters for API requests
    user_type = request.args.get('type')  # 'AI' or 'Human'
    
    # Get all users
    if request.headers.get('Accept') == 'application/json':
        try:
            # Get users with optional type filter
            users = User.get_all(user_type)
            users_data = [user.to_dict() for user in users]
            return jsonify({"users": users_data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # For HTML requests, get all users
    users_data = []
    users = User.get_all()  # Use the User model's get_all method
    
    for user in users:
        user_data = user.to_dict()  # This includes tracking_type
        user_data['id'] = user.user_id  # Add document ID
        user_data['phone'] = user.user_id  # WhatsApp number is stored in user_id
        user_data['active'] = (datetime.utcnow() - user_data.get('last_active', datetime.min).replace(tzinfo=None)).days < 7 if user_data.get('last_active') else False
        user_data['created_at'] = user_data.get('created_at', user_data.get('last_active'))
        users_data.append(user_data)
    
    return render_template('admin/users.html', users=users_data)

@admin_bp.route('/users/<user_id>', methods=['GET'])
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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
@admin_required
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
                if user.tracking_type == User.TRACKING_TYPE_AI:
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
@admin_required
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
@admin_required
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

# Traditional User Management Routes
@admin_bp.route('/traditional/users', methods=['POST'])
@admin_required
def create_traditional_user():
    """Create a new traditional (human-tracked) user"""
    try:
        data = request.json
        
        # Validate required fields
        if not all(key in data for key in ['user_id', 'name']):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Check if user already exists
        existing_user = User.get(data['user_id'])
        if existing_user:
            return jsonify({"error": "User already exists"}), 409
        
        # Create user with traditional tracking
        user = User.create(
            user_id=data['user_id'],
            name=data['name'],
            tracking_type=User.TRACKING_TYPE_HUMAN,
            input_method=User.INPUT_METHOD_BACKOFFICE
        )
        
        return jsonify({"user": user.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/traditional/checkins', methods=['POST'])
@admin_required
def create_traditional_checkin():
    """Create a new check-in for a traditional user"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['user_id', 'response', 'checkin_type']
        if not all(key in data for key in required_fields):
            return jsonify({"error": f"Missing required fields: {required_fields}"}), 400
        
        # Verify user exists and is traditional
        user = User.get(data['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user.tracking_type != User.TRACKING_TYPE_HUMAN:
            return jsonify({"error": "Check-ins can only be added for traditional users"}), 400
        
        # Create check-in
        checkin = CheckIn.create(
            user_id=data['user_id'],
            response=data['response'],
            checkin_type=data['checkin_type'],
            sentiment_score=data.get('sentiment_score'),
            tracking_type=CheckIn.TRACKING_TYPE_HUMAN,
            input_method=CheckIn.INPUT_METHOD_BACKOFFICE
        )
        
        return jsonify({"checkin": checkin.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/traditional/tasks', methods=['POST'])
@admin_required
def create_traditional_task():
    """Create a new task for a traditional user"""
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['user_id', 'description']
        if not all(key in data for key in required_fields):
            return jsonify({"error": f"Missing required fields: {required_fields}"}), 400
        
        # Verify user exists and is traditional
        user = User.get(data['user_id'])
        if not user:
            return jsonify({"error": "User not found"}), 404
        if user.tracking_type != User.TRACKING_TYPE_HUMAN:
            return jsonify({"error": "Tasks can only be added for traditional users"}), 400
        
        # Create task
        task = Task.create(
            user_id=data['user_id'],
            description=data['description'],
            status=data.get('status', Task.STATUS_PENDING),
            scheduled_date=data.get('scheduled_date'),
            tracking_type=Task.TRACKING_TYPE_HUMAN,
            input_method=Task.INPUT_METHOD_BACKOFFICE
        )
        
        return jsonify({"task": task.to_dict()}), 201
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/traditional/tasks/<task_id>', methods=['PUT'])
@admin_required
def update_traditional_task(task_id):
    """Update a traditional user's task"""
    try:
        data = request.json
        
        # Get the task
        task = Task.get(task_id)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        # Verify it's a traditional task
        if task.tracking_type != Task.TRACKING_TYPE_HUMAN:
            return jsonify({"error": "Can only update traditional tasks"}), 400
        
        # Update allowed fields
        if 'status' in data:
            task.status = data['status']
        if 'description' in data:
            task.description = data['description']
        if 'scheduled_date' in data:
            task.scheduled_date = data['scheduled_date']
        
        # Save changes
        task.update()
        
        return jsonify({"task": task.to_dict()}), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Analytics Routes
@admin_bp.route('/analytics/comparison', methods=['GET'])
@admin_required
def get_comparative_analytics():
    """Get comparative analytics between AI and traditional users"""
    try:
        # Get services
        analytics_service = get_analytics_service()
        enhanced_analytics = EnhancedAnalyticsService()
        
        # Get query parameters
        days = int(request.args.get('days', 30))
        
        # Get all users
        all_users = User.get_all()
        ai_users = [u for u in all_users if u.tracking_type == User.TRACKING_TYPE_AI]
        human_users = [u for u in all_users if u.tracking_type == User.TRACKING_TYPE_HUMAN]
        
        # Calculate metrics for both groups
        ai_metrics = calculate_group_metrics(ai_users, days)
        human_metrics = calculate_group_metrics(human_users, days)
        
        return jsonify({
            "ai_metrics": ai_metrics,
            "human_metrics": human_metrics,
            "comparison": {
                "task_completion_difference": human_metrics['task_completion_rate'] - ai_metrics['task_completion_rate'],
                "engagement_difference": human_metrics['engagement_rate'] - ai_metrics['engagement_rate'],
                "sentiment_difference": human_metrics['avg_sentiment'] - ai_metrics['avg_sentiment']
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def calculate_group_metrics(users, days):
    """Calculate metrics for a group of users"""
    if not users:
        return {
            "task_completion_rate": 0,
            "engagement_rate": 0,
            "avg_sentiment": 0,
            "total_users": 0
        }
    
    analytics_service = get_analytics_service()
    total_completion_rate = 0
    total_engagement_rate = 0
    total_sentiment = 0
    
    for user in users:
        total_completion_rate += analytics_service.get_task_completion_rate(user.user_id, days)
        total_engagement_rate += analytics_service.get_user_response_rate(user.user_id, days)
        sentiment_scores = [s for s in user.sentiment_history if s is not None]
        user_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        total_sentiment += user_sentiment
    
    num_users = len(users)
    return {
        "task_completion_rate": total_completion_rate / num_users,
        "engagement_rate": total_engagement_rate / num_users,
        "avg_sentiment": total_sentiment / num_users,
        "total_users": num_users
    } 