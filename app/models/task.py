from datetime import datetime
from config.firebase_config import get_db
import uuid
import logging
from google.cloud import firestore

logger = logging.getLogger(__name__)

class Task:
    """Task model for the accountability system"""
    
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_STUCK = 'stuck'
    
    # Tracking type constants
    TRACKING_TYPE_AI = 'AI'
    TRACKING_TYPE_HUMAN = 'HUMAN'
    
    # Input method constants
    INPUT_METHOD_WHATSAPP = 'WHATSAPP'
    INPUT_METHOD_BACKOFFICE = 'BACKOFFICE'
    
    def __init__(self, task_id=None, user_id=None, description=None, status=None, created_at=None, scheduled_date=None, completed_at=None, tracking_type=None):
        """
        Initialize a task
        
        Args:
            task_id (str, optional): Task ID. Defaults to None.
            user_id (str, optional): User ID. Defaults to None.
            description (str, optional): Task description. Defaults to None.
            status (str, optional): Task status. Defaults to None.
            created_at (datetime, optional): Creation timestamp. Defaults to None.
            scheduled_date (datetime, optional): Scheduled date. Defaults to None.
            completed_at (datetime, optional): Completion timestamp. Defaults to None.
            tracking_type (str, optional): Type of tracking. Defaults to None.
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.user_id = user_id
        self.description = description
        self.status = status or self.STATUS_PENDING
        self.created_at = created_at or datetime.now()
        self.scheduled_date = scheduled_date
        self.completed_at = completed_at
        self.tracking_type = tracking_type or self.TRACKING_TYPE_HUMAN
    
    def to_dict(self):
        """Convert the task to a dictionary"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'scheduled_date': self.scheduled_date,
            'tracking_type': self.tracking_type,
            'input_method': self.input_method
        }
    
    @classmethod
    def create(cls, user_id, description, status=STATUS_PENDING, scheduled_date=None):
        """
        Create a new task
        
        Args:
            user_id (str): User ID
            description (str): Task description
            status (str, optional): Task status. Defaults to STATUS_PENDING.
            scheduled_date (datetime, optional): Date when the task is scheduled. Defaults to None.
            
        Returns:
            Task: The created task
        """
        # Generate a unique ID
        task_id = str(uuid.uuid4())
        
        # Create task data
        task_data = {
            'user_id': user_id,
            'description': description,
            'status': status,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Add scheduled date if provided
        if scheduled_date:
            # Convert to date string for storage
            scheduled_date_str = scheduled_date.strftime('%Y-%m-%d')
            task_data['scheduled_date'] = scheduled_date_str
        
        # Save to Firestore
        db = get_db()
        db.collection('tasks').document(task_id).set(task_data)
        
        # Return task object
        created_at = datetime.now()  # Use current time as an approximation until the server timestamp is available
        return cls(task_id, user_id, description, status, created_at, scheduled_date)
    
    @staticmethod
    def get(task_id):
        """
        Get a task by ID
        
        Args:
            task_id (str): Task ID
            
        Returns:
            Task: The task, or None if not found
        """
        db = get_db()
        doc = db.collection('tasks').document(task_id).get()
        
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        user_id = data.get('user_id')
        description = data.get('description')
        status = data.get('status')
        created_at = data.get('created_at')
        
        # Convert created_at timestamp
        if isinstance(created_at, firestore.Timestamp):
            created_at = created_at.datetime
        
        # Parse scheduled date if available
        scheduled_date = None
        if 'scheduled_date' in data:
            try:
                scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
            except ValueError:
                pass
        
        return Task(task_id, user_id, description, status, created_at, scheduled_date)
    
    @classmethod
    def get_for_user(cls, user_id, status=None, scheduled_date=None):
        """
        Get tasks for a user
        
        Args:
            user_id (str): The user's ID
            status (str, optional): Filter by status
            scheduled_date (datetime, optional): Filter by scheduled date
            
        Returns:
            list: List of tasks
        """
        db = get_db()
        query = db.collection('tasks').where('user_id', '==', user_id)
        
        if status:
            query = query.where('status', '==', status)
            
        if scheduled_date:
            # Convert to datetime if needed
            if not isinstance(scheduled_date, datetime):
                scheduled_date = datetime.fromisoformat(str(scheduled_date))
            # Get start and end of day
            start_of_day = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day)
            end_of_day = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day, 23, 59, 59)
            query = query.where('scheduled_date', '>=', start_of_day)
            query = query.where('scheduled_date', '<=', end_of_day)
        
        tasks = []
        for doc in query.stream():
            data = doc.to_dict()
            # Convert timestamps
            created_at = cls._convert_timestamp(data.get('created_at'))
            scheduled_date = cls._convert_timestamp(data.get('scheduled_date'))
            completed_at = cls._convert_timestamp(data.get('completed_at'))
            
            task = cls(
                task_id=doc.id,
                user_id=data.get('user_id'),
                description=data.get('description'),
                status=data.get('status', cls.STATUS_PENDING),
                created_at=created_at,
                scheduled_date=scheduled_date,
                completed_at=completed_at,
                tracking_type=data.get('tracking_type', cls.TRACKING_TYPE_HUMAN)
            )
            tasks.append(task)
            
        return tasks
    
    @classmethod
    def get_completed_for_user(cls, user_id, start_date=None):
        """
        Get completed tasks for a user within a date range
        
        Args:
            user_id (str): The user's ID
            start_date (datetime, optional): Start date for filtering tasks. If None, gets all completed tasks.
            
        Returns:
            list: List of completed tasks
        """
        logger.debug(f"Getting completed tasks for user {user_id} from {start_date}")
        
        # Get tasks with status 'done'
        tasks = cls.get_for_user(user_id, status=cls.STATUS_DONE)
        
        # Filter by start date if provided
        if start_date:
            tasks = [t for t in tasks if t.completed_at and t.completed_at >= start_date]
            
        logger.debug(f"Found {len(tasks)} completed tasks")
        return tasks
    
    def update(self):
        """Update the task in the database"""
        self.updated_at = datetime.now()
        db = get_db()
        db.collection('tasks').document(self.task_id).update(self.to_dict())
    
    def update_status(self, status):
        """
        Update the task status
        
        Args:
            status (str): The new status
        """
        self.status = status
        if status == self.STATUS_DONE:
            self.completed_at = datetime.now()
        self.update()
    
    def delete(self):
        """Delete the task from the database"""
        db = get_db()
        db.collection('tasks').document(self.task_id).delete()

    @staticmethod
    def _convert_timestamp(timestamp):
        """Convert a timestamp to datetime"""
        if isinstance(timestamp, datetime):
            return timestamp
        if hasattr(timestamp, 'seconds'):
            # Handle server timestamp
            return datetime.fromtimestamp(timestamp.seconds)
        return None 