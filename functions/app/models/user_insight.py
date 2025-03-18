from datetime import datetime
from config.firebase_config import get_db
import uuid
from firebase_admin import firestore
import logging

logger = logging.getLogger(__name__)

class UserInsight:
    """Model for storing user insights, patterns, strategies, and obstacles"""
    
    COLLECTION = 'user_insights'
    
    # Insight types
    TYPE_STRATEGY = 'strategy'       # A strategy that worked for the user
    TYPE_OBSTACLE = 'obstacle'       # A challenge/obstacle the user faced
    TYPE_REFLECTION = 'reflection'   # A general reflection
    TYPE_TIME_PATTERN = 'time_pattern'  # Identified pattern about preferred times
    TYPE_TRIGGER = 'trigger'         # Something that triggers executive dysfunction
    
    def __init__(self, insight_id, user_id, content, insight_type, 
                 source=None, task_id=None, task_description=None,
                 effectiveness=None, created_at=None, tags=None):
        """
        Initialize a UserInsight object
        
        Args:
            insight_id (str): Unique identifier
            user_id (str): User ID this insight belongs to
            content (str): The insight content/description
            insight_type (str): Type of insight (strategy, obstacle, etc.)
            source (str): Where this insight came from (weekly reflection, analysis, etc.)
            task_id (str, optional): Related task ID if applicable
            task_description (str, optional): Description of related task
            effectiveness (int, optional): Rating of effectiveness (1-5) if applicable
            created_at (datetime): When the insight was created
            tags (list): List of tags/categories for this insight
        """
        self.insight_id = insight_id
        self.user_id = user_id
        self.content = content
        self.insight_type = insight_type
        self.source = source
        self.task_id = task_id
        self.task_description = task_description
        self.effectiveness = effectiveness
        self.created_at = created_at or datetime.now()
        self.tags = tags or []
        
    def to_dict(self):
        """Convert the insight to a dictionary"""
        data = {
            'user_id': self.user_id,
            'content': self.content,
            'insight_type': self.insight_type,
            'created_at': self.created_at,
            'tags': self.tags
        }
        
        # Add optional fields if they exist
        if self.source:
            data['source'] = self.source
        if self.task_id:
            data['task_id'] = self.task_id
        if self.task_description:
            data['task_description'] = self.task_description
        if self.effectiveness is not None:
            data['effectiveness'] = self.effectiveness
            
        return data
    
    @classmethod
    def create(cls, user_id, content, insight_type, source=None, task_id=None, 
               task_description=None, effectiveness=None, tags=None):
        """
        Create a new user insight
        
        Args:
            user_id (str): The user's ID
            content (str): The insight content
            insight_type (str): Type of insight
            source (str, optional): Source of the insight
            task_id (str, optional): Related task ID
            task_description (str, optional): Description of related task
            effectiveness (int, optional): Rating of effectiveness (1-5)
            tags (list, optional): List of tags/categories
            
        Returns:
            UserInsight: The created insight
        """
        db = get_db()
        
        # Generate a unique ID
        insight_id = str(uuid.uuid4())
        
        # Create the insight object
        insight = cls(
            insight_id=insight_id,
            user_id=user_id,
            content=content,
            insight_type=insight_type,
            source=source,
            task_id=task_id,
            task_description=task_description,
            effectiveness=effectiveness,
            tags=tags
        )
        
        # Save to database
        db.collection(cls.COLLECTION).document(insight_id).set(insight.to_dict())
        
        return insight
    
    @staticmethod
    def get(insight_id):
        """
        Get an insight by ID
        
        Args:
            insight_id (str): The insight ID
            
        Returns:
            UserInsight: The insight, or None if not found
        """
        db = get_db()
        doc = db.collection(UserInsight.COLLECTION).document(insight_id).get()
        
        if not doc.exists:
            return None
            
        data = doc.to_dict()
        return UserInsight(
            insight_id=insight_id,
            user_id=data.get('user_id'),
            content=data.get('content'),
            insight_type=data.get('insight_type'),
            source=data.get('source'),
            task_id=data.get('task_id'),
            task_description=data.get('task_description'),
            effectiveness=data.get('effectiveness'),
            created_at=data.get('created_at').datetime if data.get('created_at') else None,
            tags=data.get('tags', [])
        )
    
    @staticmethod
    def get_for_user(user_id, insight_type=None, limit=None, tags=None):
        """
        Get insights for a specific user
        
        Args:
            user_id (str): The user's ID
            insight_type (str, optional): Filter by insight type
            limit (int, optional): Max number of insights to retrieve
            tags (list, optional): Filter by tags
            
        Returns:
            list: List of UserInsight objects
        """
        db = get_db()
        query = db.collection(UserInsight.COLLECTION).where('user_id', '==', user_id)
        
        # Apply type filter
        if insight_type:
            query = query.where('insight_type', '==', insight_type)
        
        # Get results ordered by creation time (newest first)
        query = query.order_by('created_at', direction="DESCENDING")
        
        # Apply limit if specified
        if limit:
            query = query.limit(limit)
        
        # Execute query
        results = query.stream()
        
        insights = []
        for doc in results:
            data = doc.to_dict()
            
            # Filter by tags if specified
            if tags and not any(tag in data.get('tags', []) for tag in tags):
                continue
                
            insight = UserInsight(
                insight_id=doc.id,
                user_id=data.get('user_id'),
                content=data.get('content'),
                insight_type=data.get('insight_type'),
                source=data.get('source'),
                task_id=data.get('task_id'),
                task_description=data.get('task_description'),
                effectiveness=data.get('effectiveness'),
                created_at=data.get('created_at').datetime if data.get('created_at') else None,
                tags=data.get('tags', [])
            )
            insights.append(insight)
        
        return insights
    
    @staticmethod
    def get_strategies_for_task_type(user_id, task_keywords, limit=3):
        """
        Get strategies that might work for a specific type of task
        
        Args:
            user_id (str): The user's ID
            task_keywords (list): Keywords from the task
            limit (int): Maximum number of strategies to return
            
        Returns:
            list: List of relevant UserInsight objects
        """
        strategies = UserInsight.get_for_user(user_id, insight_type=UserInsight.TYPE_STRATEGY)
        
        # Score strategies based on keyword matches in content or task description
        scored_strategies = []
        for strategy in strategies:
            score = 0
            for keyword in task_keywords:
                keyword = keyword.lower()
                # Check content
                if keyword in strategy.content.lower():
                    score += 2
                # Check task description
                if strategy.task_description and keyword in strategy.task_description.lower():
                    score += 3
                # Check tags
                if any(keyword in tag.lower() for tag in strategy.tags):
                    score += 2
            
            # Consider effectiveness if available
            if strategy.effectiveness is not None:
                score += strategy.effectiveness
                
            scored_strategies.append((strategy, score))
        
        # Sort by score (highest first) and take the top strategies
        scored_strategies.sort(key=lambda x: x[1], reverse=True)
        top_strategies = [s[0] for s in scored_strategies[:limit]]
        
        return top_strategies
    
    def update(self):
        """Update the insight in the database"""
        db = get_db()
        db.collection(self.COLLECTION).document(self.insight_id).update(self.to_dict())
    
    def update_effectiveness(self, effectiveness):
        """
        Update the effectiveness rating of this insight
        
        Args:
            effectiveness (int): New effectiveness rating (1-5)
        """
        self.effectiveness = effectiveness
        self.update()
    
    def add_tag(self, tag):
        """
        Add a tag to this insight
        
        Args:
            tag (str): Tag to add
        """
        if tag not in self.tags:
            self.tags.append(tag)
            self.update()
    
    def remove_tag(self, tag):
        """
        Remove a tag from this insight
        
        Args:
            tag (str): Tag to remove
        """
        if tag in self.tags:
            self.tags.remove(tag)
            self.update() 