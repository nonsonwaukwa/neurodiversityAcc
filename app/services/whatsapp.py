import requests
import json
import os
from flask import current_app
import re
import logging
import base64

logger = logging.getLogger(__name__)

class WhatsAppService:
    """Service for interacting with the WhatsApp Business API"""
    
    def __init__(self, account_index=0):
        """
        Initialize the WhatsApp service
        
        Args:
            account_index (int): Index of the Meta account to use (0 or 1)
        """
        self.account_index = account_index
        self.api_url = current_app.config.get('WHATSAPP_API_URL')
        
        # Get credentials for the specified account
        phone_number_ids = current_app.config.get('WHATSAPP_PHONE_NUMBER_IDS', [])
        access_tokens = current_app.config.get('WHATSAPP_ACCESS_TOKENS', [])
        
        if not phone_number_ids or not access_tokens or len(phone_number_ids) <= account_index or len(access_tokens) <= account_index:
            raise ValueError(f"WhatsApp API configuration for account {account_index} is incomplete")
        
        self.phone_number_id = phone_number_ids[account_index]
        self.access_token = access_tokens[account_index]
        
        if not all([self.api_url, self.phone_number_id, self.access_token]):
            raise ValueError(f"WhatsApp API configuration for account {account_index} is incomplete")
    
    def send_message(self, recipient_number, message_text):
        """
        Send a text message to a WhatsApp user
        
        Args:
            recipient_number (str): The recipient's WhatsApp number
            message_text (str): The message to send
            
        Returns:
            dict: The API response
        """
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': recipient_number,
            'type': 'text',
            'text': {
                'body': message_text
            }
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        return response.json() if response.status_code == 200 else None
    
    def send_interactive_message(self, recipient_number, header_text, body_text, buttons):
        """
        Send an interactive message with buttons
        
        Args:
            recipient_number (str): The recipient's WhatsApp number
            header_text (str): The header text
            body_text (str): The body text
            buttons (list): List of button objects with 'id' and 'title'
            
        Returns:
            dict: The API response
        """
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        button_objects = [
            {
                'type': 'reply',
                'reply': {
                    'id': button['id'],
                    'title': button['title']
                }
            }
            for button in buttons
        ]
        
        data = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': recipient_number,
            'type': 'interactive',
            'interactive': {
                'type': 'button',
                'header': {
                    'type': 'text',
                    'text': header_text
                },
                'body': {
                    'text': body_text
                },
                'action': {
                    'buttons': button_objects
                }
            }
        }
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        return response.json() if response.status_code == 200 else None
    
    def send_template_message(self, recipient_number, template_name, components=None):
        """
        Send a template message
        
        Args:
            recipient_number (str): The recipient's WhatsApp number
            template_name (str): The name of the template
            components (list, optional): Template components
            
        Returns:
            dict: The API response
        """
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messaging_product': 'whatsapp',
            'recipient_type': 'individual',
            'to': recipient_number,
            'type': 'template',
            'template': {
                'name': template_name,
                'language': {
                    'code': 'en_US'
                }
            }
        }
        
        if components:
            data['template']['components'] = components
        
        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        return response.json() if response.status_code == 200 else None
    
    def verify_webhook(self, request_args):
        """
        Verify the webhook challenge from WhatsApp
        
        Args:
            request_args: The request arguments
            
        Returns:
            str or bool: Challenge string if verification succeeded, False otherwise
        """
        mode = request_args.get('hub.mode')
        token = request_args.get('hub.verify_token')
        challenge = request_args.get('hub.challenge')
        
        verify_token = current_app.config.get('WHATSAPP_VERIFY_TOKEN', os.environ.get('WHATSAPP_VERIFY_TOKEN'))
        
        if not verify_token:
            verify_token = 'odinma_accountability_webhook'  # Default token
        
        # Check if the mode and token are as expected
        if mode == 'subscribe' and token == verify_token:
            return challenge
        
        return False
    
    def parse_webhook_data(self, data):
        """
        Parse webhook data from WhatsApp
        
        Args:
            data: The webhook data
            
        Returns:
            dict: Parsed message data
        """
        result = {
            'messages': []
        }
        
        try:
            if 'object' in data and data['object'] == 'whatsapp_business_account':
                entries = data.get('entry', [])
                
                for entry in entries:
                    changes = entry.get('changes', [])
                    
                    for change in changes:
                        value = change.get('value', {})
                        messages = value.get('messages', [])
                        
                        # Get the phone number ID from the metadata
                        metadata = value.get('metadata', {})
                        phone_number_id = metadata.get('phone_number_id')
                        
                        # Determine which account this belongs to
                        account_index = self._get_account_index(phone_number_id)
                        
                        for message in messages:
                            from_number = message.get('from')
                            message_id = message.get('id')
                            timestamp = message.get('timestamp')
                            
                            message_obj = {
                                'from': from_number,
                                'id': message_id,
                                'timestamp': timestamp,
                                'type': message.get('type'),
                                'account_index': account_index
                            }
                            
                            # Handle different message types
                            if message.get('type') == 'text':
                                message_obj['text'] = message.get('text', {}).get('body', '')
                            
                            elif message.get('type') == 'interactive':
                                interactive = message.get('interactive', {})
                                if interactive.get('type') == 'button_reply':
                                    button_reply = interactive.get('button_reply', {})
                                    message_obj['button_id'] = button_reply.get('id')
                                    message_obj['button_text'] = button_reply.get('title')
                            
                            elif message.get('type') == 'audio':
                                audio = message.get('audio', {})
                                message_obj['audio_id'] = audio.get('id')
                                message_obj['audio_mime_type'] = audio.get('mime_type')
                                message_obj['audio_url'] = audio.get('url')
                            
                            # Add other message types as needed (e.g., location)
                            
                            result['messages'].append(message_obj)
        
        except Exception as e:
            print(f"Error parsing webhook data: {e}")
        
        return result
    
    def _get_account_index(self, phone_number_id):
        """
        Get the account index for a given phone number ID
        
        Args:
            phone_number_id (str): The WhatsApp phone number ID
            
        Returns:
            int: The account index (0 or 1)
        """
        phone_number_ids = current_app.config.get('WHATSAPP_PHONE_NUMBER_IDS', [])
        
        try:
            return phone_number_ids.index(phone_number_id)
        except ValueError:
            # Default to account 0 if not found
            return 0

    def send_interactive_buttons(self, to, body, buttons):
        """
        Send an interactive message with buttons
        
        Args:
            to (str): Recipient WhatsApp number with country code
            body (str): Message body
            buttons (list): List of button objects, each with 'id' and 'title'
            
        Returns:
            dict: Response from the WhatsApp API
        """
        # Validate number (remove any non-numeric chars)
        to = re.sub(r'[^0-9]', '', to)
        
        # Format buttons for WhatsApp API
        formatted_buttons = []
        for button in buttons:
            formatted_buttons.append({
                "type": "reply",
                "reply": {
                    "id": button['id'],
                    "title": button['title']
                }
            })
        
        # Create request data
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body
                },
                "action": {
                    "buttons": formatted_buttons
                }
            }
        }
        
        try:
            # Make request to WhatsApp API
            response = requests.post(
                f"{self.api_url}/messages",
                json=data,
                headers=self.get_headers()
            )
            
            # Parse response
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error sending interactive message: {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Exception sending interactive message: {e}")
            return None

    def send_image(self, recipient_number, image_path, caption=None):
        """
        Send an image to a WhatsApp user
        
        Args:
            recipient_number (str): The recipient's WhatsApp number
            image_path (str): Path to the image file
            caption (str, optional): Caption for the image
            
        Returns:
            dict: The API response
        """
        # Validate number (remove any non-numeric chars)
        recipient_number = re.sub(r'[^0-9]', '', recipient_number)
        
        # Read the image file
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
            
            # Encode the image to base64
            encoded_image = base64.b64encode(image_data).decode('utf-8')
            
            # Create request data
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient_number,
                "type": "image",
                "image": {
                    "caption": caption if caption else "",
                    "data": encoded_image
                }
            }
            
            # Make request to WhatsApp API
            response = requests.post(
                f"{self.api_url}/{self.phone_number_id}/messages",
                json=data,
                headers=self.get_headers()
            )
            
            # Parse response
            if response.status_code == 200:
                logger.info(f"Successfully sent image to {recipient_number}")
                return response.json()
            else:
                logger.error(f"Error sending image: {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Error sending image: {e}")
            return None
    
    def get_headers(self):
        """
        Get headers for WhatsApp API requests
        
        Returns:
            dict: Headers for WhatsApp API requests
        """
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

# Create an instance of the service
def get_whatsapp_service(account_index=0):
    """
    Get an instance of the WhatsApp service
    
    Args:
        account_index (int, optional): The account index (0 or 1)
        
    Returns:
        WhatsAppService: The WhatsApp service instance
    """
    return WhatsAppService(account_index)

def get_whatsapp_service_for_number(user_id):
    """
    Get the appropriate WhatsApp service instance for a user ID
    
    Args:
        user_id (str): The user's WhatsApp number
        
    Returns:
        WhatsAppService: The WhatsApp service instance
    """
    from app.models.user import User
    
    # Get the user to check which account they belong to
    user = User.get(user_id)
    
    if user and hasattr(user, 'account_index'):
        return WhatsAppService(user.account_index)
    
    # Default to account 0 if user doesn't exist or doesn't have an account_index
    return WhatsAppService(0) 