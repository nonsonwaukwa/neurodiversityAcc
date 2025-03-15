from datetime import datetime
from config.firebase_config import get_db

class Task:
    """Task model representing a user task in the system"""
    
    COLLECTION = 'tasks'
    
    # Task status constants
    STATUS_PENDING = 'Pending'
    STATUS_DONE = 'Done'
    STATUS_STUCK = 'Stuck'
    STATUS_IN_PROGRESS = 'In Progress'
    
    # Task category constants
    CATEGORY_WORK = 'Work'
    CATEGORY_PERSONAL = 'Personal'
    CATEGORY_HEALTH = 'Health'
    CATEGORY_OTHER = 'Other'
    
    def __init__(self, task_id, user_id, description, category=CATEGORY_OTHER, 
                 status=STATUS_PENDING, created_at=None, updated_at=None, used_hack=False):
        """
        Initialize a Task object
        
        Args:
            task_id (str): Unique identifier
            user_id (str): User ID this task belongs to
            description (str): Task description
            category (str): Task category
            status (str): Task status
            created_at (datetime): Task creation time
            updated_at (datetime): Last update time
            used_hack (bool): Whether an ADHD-friendly hack was used
        """
        self.task_id = task_id
        self.user_id = user_id
        self.description = description
        self.category = category
        self.status = status
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.used_hack = used_hack
    
    @classmethod
    def create(cls, user_id, description, category=CATEGORY_OTHER):
        """
        Create a new task for a user
        
        Args:
            user_id (str): User ID this task belongs to
            description (str): Task description
            category (str): Task category
            
        Returns:
            Task: The created task object
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        task = cls(task_id, user_id, description, category)
        
        # Convert to dictionary for Firestore
        task_data = {
            'task_id': task.task_id,
            'user_id': task.user_id,
            'description': task.description,
            'category': task.category,
            'status': task.status,
            'created_at': task.created_at,
            'updated_at': task.updated_at,
            'used_hack': task.used_hack
        }
        
        # Add to Firestore
        get_db().collection(cls.COLLECTION).document(task_id).set(task_data)
        
        return task
    
    @classmethod
    def get(cls, task_id):
        """
        Retrieve a task from the database
        
        Args:
            task_id (str): The task's ID
            
        Returns:
            Task: The task object if found, None otherwise
        """
        doc = get_db().collection(cls.COLLECTION).document(task_id).get()
        
        if not doc.exists:
            return None
        
        task_data = doc.to_dict()
        return cls(
            task_id=task_data.get('task_id'),
            user_id=task_data.get('user_id'),
            description=task_data.get('description'),
            category=task_data.get('category'),
            status=task_data.get('status'),
            created_at=task_data.get('created_at'),
            updated_at=task_data.get('updated_at'),
            used_hack=task_data.get('used_hack', False)
        )
    
    @classmethod
    def get_for_user(cls, user_id, status=None, limit=None):
        """
        Retrieve tasks for a specific user, optionally filtered by status
        
        Args:
            user_id (str): The user's ID
            status (str, optional): Filter by task status
            limit (int, optional): Maximum number of tasks to retrieve
            
        Returns:
            list: List of Task objects
        """
        query = get_db().collection(cls.COLLECTION).where('user_id', '==', user_id)
        
        if status:
            query = query.where('status', '==', status)
        
        # Order by creation date (newest first)
        query = query.order_by('created_at', direction='DESCENDING')
        
        if limit:
            query = query.limit(limit)
        
        docs = query.stream()
        
        tasks = []
        for doc in docs:
            task_data = doc.to_dict()
            tasks.append(cls(
                task_id=task_data.get('task_id'),
                user_id=task_data.get('user_id'),
                description=task_data.get('description'),
                category=task_data.get('category'),
                status=task_data.get('status'),
                created_at=task_data.get('created_at'),
                updated_at=task_data.get('updated_at'),
                used_hack=task_data.get('used_hack', False)
            ))
        
        return tasks
    
    def update_status(self, new_status):
        """
        Update the task's status
        
        Args:
            new_status (str): The new status
        """
        self.status = new_status
        self.updated_at = datetime.now()
        
        get_db().collection(self.COLLECTION).document(self.task_id).update({
            'status': self.status,
            'updated_at': self.updated_at
        })
    
    def mark_hack_used(self):
        """Mark that an ADHD-friendly hack was used for this task"""
        self.used_hack = True
        self.updated_at = datetime.now()
        
        get_db().collection(self.COLLECTION).document(self.task_id).update({
            'used_hack': self.used_hack,
            'updated_at': self.updated_at
        })
    
    def to_dict(self):
        """Convert the task object to a dictionary"""
        return {
            'task_id': self.task_id,
            'user_id': self.user_id,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'used_hack': self.used_hack
        } 