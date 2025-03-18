from functools import wraps
from flask import session, redirect, url_for, current_app
import firebase_admin
from firebase_admin import auth
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning("No user_id in session")
            return redirect(url_for('admin.login'))
            
        try:
            # Get user from Firebase
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("Invalid user_id in session")
                session.clear()
                return redirect(url_for('admin.login'))

            user = auth.get_user(user_id)
            
            # Check if user has admin claim
            if not user.custom_claims or not user.custom_claims.get('admin'):
                logger.warning(f"Non-admin user attempted to access admin route: {user.uid}")
                session.clear()
                return redirect(url_for('admin.login'))
                
            return f(*args, **kwargs)
            
        except auth.UserNotFoundError:
            logger.warning(f"User not found in Firebase: {session.get('user_id')}")
            session.clear()
            return redirect(url_for('admin.login'))
        except Exception as e:
            logger.error(f"Error in admin authentication: {str(e)}", exc_info=True)
            session.clear()
            return redirect(url_for('admin.login'))
            
    return decorated_function

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token
    
    Args:
        id_token (str): The Firebase ID token to verify
        
    Returns:
        dict: The decoded token claims
        
    Raises:
        ValueError: If token is invalid
    """
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        
        # Get user
        user = auth.get_user(decoded_token['uid'])
        
        # Check admin claim
        if not user.custom_claims or not user.custom_claims.get('admin'):
            raise ValueError('User is not an admin')
            
        # Return user data in a format that can be serialized to session
        return {
            'uid': user.uid,
            'email': user.email,
            'display_name': user.display_name,
            'is_admin': True
        }
        
    except auth.InvalidIdTokenError:
        raise ValueError('Invalid token')
    except auth.ExpiredIdTokenError:
        raise ValueError('Token has expired')
    except auth.RevokedIdTokenError:
        raise ValueError('Token has been revoked')
    except auth.UserNotFoundError:
        raise ValueError('User not found')
    except Exception as e:
        logger.error(f"Error verifying token: {str(e)}", exc_info=True)
        raise ValueError('Authentication failed') 