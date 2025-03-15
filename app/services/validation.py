from typing import Tuple, Optional

class ResponseValidator:
    @staticmethod
    def validate_feeling_response(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a response contains emotional/feeling content
        Returns: (is_valid, feedback_message)
        """
        feeling_indicators = [
            "feel", "feeling", "felt", "mood", "am", "doing",
            "happy", "sad", "okay", "ok", "good", "bad", "great", "terrible",
            "excited", "worried", "anxious", "calm", "stressed", "relaxed",
            "overwhelmed", "confident", "tired", "energetic", "meh",
            "😊", "😔", "😢", "😃", "😕", "🙂", "☹️", "😴", "😫"
        ]
        
        text_lower = text.lower()
        has_feeling = any(indicator in text_lower for indicator in feeling_indicators)
        
        if not has_feeling:
            return False, "I'd love to know how you're feeling. Could you tell me more about your emotional state?"
        
        return True, None

    @staticmethod
    def validate_task_response(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a response contains valid task descriptions
        Returns: (is_valid, feedback_message)
        """
        # Check if text is too short
        if len(text.strip()) < 3:
            return False, "Could you provide more detail about the task you'd like to work on?"
            
        # Check if it's just a greeting or common non-task response
        common_non_tasks = ["hi", "hello", "hey", "ok", "okay", "yes", "no", "thanks", "thank you"]
        if text.lower().strip() in common_non_tasks:
            return False, "What specific task would you like to work on today?"
            
        return True, None

    @staticmethod
    def validate_task_update(text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if a response contains valid task update information
        Returns: (is_valid, feedback_message)
        """
        update_indicators = ["done", "complete", "finished", "stuck", "help", "progress", "working", "started"]
        
        text_lower = text.lower()
        has_update = any(indicator in text_lower for indicator in update_indicators)
        
        if not has_update:
            return False, "Could you let me know if you've completed the task, are stuck, or making progress?"
            
        return True, None 