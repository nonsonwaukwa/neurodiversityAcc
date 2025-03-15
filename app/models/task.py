from datetime import datetime
from config.firebase_config import get_db
import uuid
import logging

logger = logging.getLogger(__name__)

class Task:
    """Task model for the accountability system"""
    
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_STUCK = 'stuck'
    
    def __init__(self, task_id=None, user_id=None, description=None, status=None, 
                 scheduled_date=None, created_at=None, updated_at=None):
        """
        Initialize a task
        
        Args:
            task_id (str): Unique task identifier
            user_id (str): The user's WhatsApp number
            description (str): Task description
            status (str): Task status (pending, in_progress, done, stuck)
            scheduled_date (datetime): Date the task is scheduled for
            created_at (datetime): When the task was created
            updated_at (datetime): When the task was last updated
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.user_id = user_id
        self.description = description
        self.status = status or self.STATUS_PENDING
        self.scheduled_date = scheduled_date
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self):
        """Convert the task to a dictionary"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'description': self.description,
            'status': self.status,
            'scheduled_date': self.scheduled_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create a task from a dictionary"""
        return cls(
            task_id=data.get('task_id'),
            user_id=data.get('user_id'),
            description=data.get('description'),
            status=data.get('status'),
            scheduled_date=data.get('scheduled_date'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )
    
    @classmethod
    def create(cls, user_id, description, scheduled_date=None):
        """
        Create a new task
        
        Args:
            user_id (str): The user's WhatsApp number
            description (str): Task description
            scheduled_date (datetime, optional): Date the task is scheduled for
            
        Returns:
            Task: The created task
        """
        db = get_db()
        
        # Create task object
        task = cls(
            user_id=user_id,
            description=description,
            scheduled_date=scheduled_date
        )
        
        # Save to database
        db.collection('tasks').document(task.task_id).set(task.to_dict())
        
        return task
    
    @classmethod
    def get(cls, task_id):
        """
        Get a task by ID
        
        Args:
            task_id (str): The task ID
            
        Returns:
            Task: The task, or None if not found
        """
        db = get_db()
        doc = db.collection('tasks').document(task_id).get()
        
        if doc.exists:
            return cls.from_dict(doc.to_dict())
        
        return None
    
    @classmethod
    def get_for_user(cls, user_id, status=None, scheduled_date=None):
        """
        Get tasks for a specific user
        
        Args:
            user_id (str): The user's WhatsApp number
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
            # Convert to datetime with time set to 00:00:00
            if isinstance(scheduled_date, datetime):
                start_date = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day)
                end_date = datetime(scheduled_date.year, scheduled_date.month, scheduled_date.day, 23, 59, 59)
                query = query.where('scheduled_date', '>=', start_date).where('scheduled_date', '<=', end_date)
        
        tasks = []
        for doc in query.stream():
            tasks.append(cls.from_dict(doc.to_dict()))
        
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