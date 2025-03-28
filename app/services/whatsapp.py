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
        
        # Get base API URL, ensure it doesn't end with a slash
        api_url = current_app.config.get('WHATSAPP_API_URL')
        if not api_url:
            api_url = os.environ.get('WHATSAPP_API_URL', 'https://graph.facebook.com/v17.0')
        self.api_url = api_url.rstrip('/')
        
        # Get credentials for the specified account
        phone_number_ids = current_app.config.get('WHATSAPP_PHONE_NUMBER_IDS', [])
        access_tokens = current_app.config.get('WHATSAPP_ACCESS_TOKENS', [])
        
        # If not in config, try environment variables
        if not phone_number_ids:
            phone_number_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
            if phone_number_id:
                phone_number_ids = [phone_number_id]
                logger.info("Using phone number ID from environment variable")
        
        if not access_tokens:
            access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
            if access_token:
                access_tokens = [access_token]
                logger.info("Using access token from environment variable")
        
        logger.debug(f"API URL: {self.api_url}")
        logger.debug(f"Phone Number IDs available: {len(phone_number_ids) if phone_number_ids else 0}")
        logger.debug(f"Access Tokens available: {len(access_tokens) if access_tokens else 0}")
        
        if not phone_number_ids or not access_tokens or len(phone_number_ids) <= account_index or len(access_tokens) <= account_index:
            error_msg = f"WhatsApp API configuration for account {account_index} is incomplete:"
            error_msg += f"\n- Phone Number IDs: {'Yes' if phone_number_ids else 'No'}"
            error_msg += f"\n- Access Tokens: {'Yes' if access_tokens else 'No'}"
            error_msg += f"\n- Account Index Valid: {'Yes' if phone_number_ids and len(phone_number_ids) > account_index else 'No'}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.phone_number_id = phone_number_ids[account_index]
        self.access_token = access_tokens[account_index]
        
        if not all([self.api_url, self.phone_number_id, self.access_token]):
            error_msg = "WhatsApp API configuration is incomplete:"
            error_msg += f"\n- API URL: {'Yes' if self.api_url else 'No'}"
            error_msg += f"\n- Phone Number ID: {'Yes' if self.phone_number_id else 'No'}"
            error_msg += f"\n- Access Token: {'Yes' if self.access_token else 'No'}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Initialized WhatsApp service with API URL: {self.api_url}")
        logger.info(f"Using phone number ID: {self.phone_number_id}")
    
    def _get_message_url(self):
        """Get the properly formatted URL for sending messages"""
        return f"{self.api_url}/{self.phone_number_id}/messages"
    
    def send_message(self, recipient_id, message):
        """Send a message to a recipient."""
        logger = logging.getLogger(__name__)
        
        try:
            # Log the request details
            logger.debug(f"Sending message to {recipient_id}")
            logger.debug(f"Message content: {message}")
            
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            logger.debug(f"API URL: {url}")
            
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": recipient_id,
                "type": "text",
                "text": {"body": message}
            }
            logger.debug(f"Request data: {data}")
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            logger.debug("Headers set (token hidden)")
            
            response = requests.post(url, json=data, headers=headers)
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                logger.info(f"Message sent successfully. Response: {response_data}")
                return True
            else:
                logger.error(f"Failed to send message. Status code: {response.status_code}")
                logger.error(f"Error response: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error while sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while sending message: {e}")
            return False
    
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
        """Get the authorization headers for WhatsApp API requests"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
    def check_connection(self):
        """
        Check if the WhatsApp API credentials are working
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Try to get the business profile info as a simple connection test
            url = f"{self.api_url}/{self.phone_number_id}"
            headers = self.get_headers()
            
            logger.info(f"Testing WhatsApp API connection to: {url}")
            logger.info(f"Using phone number ID: {self.phone_number_id}")
            logger.info(f"API URL base: {self.api_url}")
            
            # Log headers without the actual token
            debug_headers = headers.copy()
            if 'Authorization' in debug_headers:
                debug_headers['Authorization'] = 'Bearer <token-hidden>'
            logger.debug(f"Request headers: {debug_headers}")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            logger.debug(f"Response status code: {response.status_code}")
            logger.debug(f"Response content: {response.text}")
            
            if response.status_code == 200:
                logger.info("WhatsApp API connection successful")
                return True
            else:
                logger.error(f"WhatsApp API connection failed: {response.status_code} - {response.text}")
                # Check specific error conditions
                try:
                    error_data = response.json().get('error', {})
                    error_code = error_data.get('code')
                    error_subcode = error_data.get('error_subcode')
                    logger.error(f"Error code: {error_code}, subcode: {error_subcode}")
                    
                    if error_code == 190:
                        logger.error("Invalid or expired access token")
                    elif error_code == 100:
                        if error_subcode == 33:
                            logger.error("Phone number ID not found or no permission to access it")
                        else:
                            logger.error("Invalid phone number ID or API version")
                except:
                    pass
                return False
            
        except Exception as e:
            logger.error(f"Error checking WhatsApp API connection: {str(e)}")
            return False
            
    def get_account_info(self):
        """
        Get information about the WhatsApp account
        
        Returns:
            dict: Account information if successful, None otherwise
        """
        try:
            url = f"{self.api_url}/{self.phone_number_id}"
            headers = self.get_headers()
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "phone_number_id": self.phone_number_id,
                    "account_status": "active",
                    "response_data": data
                }
            else:
                logger.error(f"Failed to get account info: {response.status_code} - {response.text}")
                return {
                    "phone_number_id": self.phone_number_id,
                    "account_status": "error",
                    "error_details": {
                        "status_code": response.status_code,
                        "response": response.text
                    }
                }
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return None

    def send_interactive_with_fallback(self, to, header_text, body_text, buttons):
        """
        Attempts to send an interactive message with buttons, falls back to numbered options if not available.
        
        Args:
            to (str): Recipient phone number
            header_text (str): Header text for the message
            body_text (str): Main body text
            buttons (list): List of button objects with 'id' and 'title' keys
        
        Returns:
            bool: Success status
        """
        try:
            # First attempt to send interactive message
            url = self._get_message_url()
            logger.debug(f"Sending interactive message to URL: {url}")
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "header": {
                        "type": "text",
                        "text": header_text
                    },
                    "body": {
                        "text": body_text
                    },
                    "action": {
                        "buttons": [{"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}} for btn in buttons]
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            logger.debug(f"Interactive message response: {response.text}")
            
            # If interactive message succeeds, return True
            if response.status_code == 200:
                logger.info(f"Successfully sent interactive message to {to}")
                return True
            
            # If we get an error about test mode or interactive messages not being available,
            # fall back to numbered response
            logger.warning(f"Interactive message failed: {response.text}. Falling back to numbered response.")
            
            # Format numbered response
            numbered_message = f"{header_text}\n\n{body_text}\n\n"
            for i, btn in enumerate(buttons, 1):
                numbered_message += f"{i}. {btn['title']}\n"
            numbered_message += "\nJust reply with the number of your choice."
            
            # Send as regular message
            return self.send_message(to, numbered_message)
        
        except Exception as e:
            logger.error(f"Error sending interactive message with fallback: {str(e)}")
            return False

    def send_list_message_with_fallback(self, to, header_text, body_text, button_text, sections):
        """
        Attempts to send a list message, falls back to numbered options if not available.
        
        Args:
            to (str): Recipient phone number
            header_text (str): Header text for the message
            body_text (str): Main body text
            button_text (str): Text for the list button (e.g., "View Options")
            sections (list): List of section objects, each containing:
                - title: Section title
                - rows: List of row objects with 'id' and 'title' (and optional 'description')
        
        Returns:
            bool: Success status
        """
        try:
            # First attempt to send list message
            url = self._get_message_url()
            logger.debug(f"Sending list message to URL: {url}")
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "header": {
                        "type": "text",
                        "text": header_text
                    },
                    "body": {
                        "text": body_text
                    },
                    "action": {
                        "button": button_text,
                        "sections": sections
                    }
                }
            }
            
            response = requests.post(url, headers=headers, json=data)
            logger.debug(f"List message response: {response.text}")
            
            # If list message succeeds, return True
            if response.status_code == 200:
                logger.info(f"Successfully sent list message to {to}")
                return True
            
            # If we get an error, fall back to numbered response
            logger.warning(f"List message failed: {response.text}. Falling back to numbered response.")
            
            # Format numbered response
            numbered_message = f"{header_text}\n\n{body_text}\n\n"
            option_number = 1
            
            for section in sections:
                numbered_message += f"\n{section['title']}:\n"
                for row in section['rows']:
                    numbered_message += f"{option_number}. {row['title']}"
                    if 'description' in row:
                        numbered_message += f" - {row['description']}"
                    numbered_message += "\n"
                    option_number += 1
            
            numbered_message += "\nJust reply with the number of your choice."
            
            # Send as regular message
            return self.send_message(to, numbered_message)
            
        except Exception as e:
            logger.error(f"Error sending list message with fallback: {str(e)}")
            return False

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