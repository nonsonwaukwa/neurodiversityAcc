from functools import wraps
from flask import request, redirect, url_for, session, current_app
import firebase_admin
from firebase_admin import auth
import logging

logger = logging.getLogger(__name__)

def admin_required(f):
    """Decorator to require admin authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if 'user_id' not in session:
            return redirect(url_for('admin.login'))
        
        try:
            # Verify the Firebase ID token
            user = auth.get_user(session['user_id'])
            
            # Check if user has admin claim
            if not user.custom_claims or not user.custom_claims.get('admin'):
                logger.warning(f"Non-admin user {user.uid} attempted to access admin route")
                return redirect(url_for('admin.login'))
            
            return f(*args, **kwargs)
            
        except auth.InvalidIdTokenError:
            # Token is invalid or expired
            session.clear()
            return redirect(url_for('admin.login'))
        except auth.UserNotFoundError:
            # User no longer exists
            session.clear()
            return redirect(url_for('admin.login'))
        except Exception as e:
            logger.error(f"Error in admin authentication: {str(e)}")
            session.clear()
            return redirect(url_for('admin.login'))
    
    return decorated_function

def verify_firebase_token(token):
    """Verify Firebase ID token and return user info"""
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
        
        # Get the user
        user = auth.get_user(user_id)
        
        # Check admin claim
        if not user.custom_claims or not user.custom_claims.get('admin'):
            raise ValueError("User is not an admin")
        
        return user
        
    except auth.InvalidIdTokenError:
        raise ValueError("Invalid token")
    except auth.ExpiredIdTokenError:
        raise ValueError("Token has expired")
    except auth.RevokedIdTokenError:
        raise ValueError("Token has been revoked")
    except auth.UserNotFoundError:
        raise ValueError("User not found")
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        raise ValueError("Authentication failed") 