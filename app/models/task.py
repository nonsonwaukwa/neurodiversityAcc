from datetime import datetime
from config.firebase_config import get_db
import uuid
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.field_filter import FieldFilter
from google.cloud.firestore_v1.field_path import FieldPath
from google.cloud.firestore_v1.document import DocumentSnapshot
from google.cloud.firestore_v1.timestamp import DatetimeWithNanoseconds

logger = logging.getLogger(__name__)

class Task:
    """Task model for the accountability system"""
    
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_STUCK = 'stuck'
    
    def __init__(self, task_id, user_id, description, status=STATUS_PENDING, created_at=None, scheduled_date=None):
        """
        Initialize a task
        
        Args:
            task_id (str): Unique task identifier
            user_id (str): The user's WhatsApp number
            description (str): Task description
            status (str): Task status (pending, in_progress, done, stuck)
            created_at (datetime): When the task was created
            scheduled_date (datetime): Date the task is scheduled for
        """
        self.task_id = task_id
        self.user_id = user_id
        self.description = description
        self.status = status
        self.created_at = created_at or datetime.now()
        self.scheduled_date = scheduled_date  # For weekly planning, tasks can be scheduled for specific days
    
    def to_dict(self):
        """Convert the task to a dictionary"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at,
            'scheduled_date': self.scheduled_date
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
        if created_at:
            created_at = created_at.datetime
        
        # Parse scheduled date if available
        scheduled_date = None
        if 'scheduled_date' in data:
            try:
                scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
            except ValueError:
                pass
        
        return Task(task_id, user_id, description, status, created_at, scheduled_date)
    
    @staticmethod
    def get_for_user(user_id, status=None, scheduled_date=None):
        """
        Get tasks for a user
        
        Args:
            user_id (str): User ID
            status (str, optional): Filter by task status. Defaults to None.
            scheduled_date (datetime, optional): Filter by scheduled date. Defaults to None.
            
        Returns:
            list: List of Task objects
        """
        db = get_db()
        query = db.collection('tasks').where('user_id', '==', user_id)
        
        # Apply status filter if provided
        if status:
            if isinstance(status, list):
                # If status is a list, use "in" operator
                query = query.where('status', 'in', status)
            else:
                query = query.where('status', '==', status)
        
        # Apply scheduled date filter if provided
        if scheduled_date:
            # Convert to date string for comparison
            date_str = scheduled_date.strftime('%Y-%m-%d')
            query = query.where('scheduled_date', '==', date_str)
        
        # Execute query
        results = query.stream()
        
        tasks = []
        for doc in results:
            task_id = doc.id
            data = doc.to_dict()
            description = data.get('description')
            task_status = data.get('status')
            
            # Handle Firestore timestamp
            created_at = data.get('created_at')
            if isinstance(created_at, firestore.Timestamp):
                created_at = created_at.datetime.replace(tzinfo=None)  # Convert to naive datetime
            
            # Parse scheduled date if available
            task_scheduled_date = None
            if 'scheduled_date' in data:
                try:
                    task_scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d')
                except ValueError:
                    pass
            
            task = Task(task_id, user_id, description, task_status, created_at, task_scheduled_date)
            tasks.append(task)
        
        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at if t.created_at else datetime.min, reverse=True)
        
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
        self.update()
    
    def delete(self):
        """Delete the task from the database"""
        db = get_db()
        db.collection('tasks').document(self.task_id).delete() 