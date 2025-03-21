#!/usr/bin/env python3
"""
WhatsApp Configuration Checker

This script checks if all required WhatsApp API environment variables are set correctly
and provides guidance on how to fix any missing or incorrect configurations.
"""

import os
import logging
import sys
from app import create_app
import dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Required environment variables for WhatsApp API
REQUIRED_WHATSAPP_VARS = [
    "WHATSAPP_API_URL",
    "WHATSAPP_PHONE_ID_0",
    "WHATSAPP_ACCESS_TOKEN_0"
]

# Optional environment variables
OPTIONAL_WHATSAPP_VARS = [
    "WHATSAPP_PHONE_ID_1", 
    "WHATSAPP_ACCESS_TOKEN_1",
    "WHATSAPP_PHONE_ID_2",
    "WHATSAPP_ACCESS_TOKEN_2"
]

def check_env_var(var_name):
    """
    Check if an environment variable is set and return its value or None
    """
    value = os.environ.get(var_name)
    if value:
        # Return masked value for tokens to avoid revealing sensitive information
        if "TOKEN" in var_name and value:
            visible_chars = 4  # Show only first 4 chars
            if len(value) > visible_chars:
                return f"{value[:visible_chars]}{'*' * (len(value) - visible_chars)}"
            return "****"  # Fallback if token is very short
        return value
    return None

def check_whatsapp_config():
    """
    Check WhatsApp API configuration and log findings
    """
    success = True
    missing_vars = []
    configured_vars = []
    
    logger.info("Checking WhatsApp API configuration...")
    
    # Check required variables
    for var in REQUIRED_WHATSAPP_VARS:
        value = check_env_var(var)
        if value:
            configured_vars.append((var, value))
            logger.info(f"✅ {var} is set to: {value}")
        else:
            missing_vars.append(var)
            logger.error(f"❌ {var} is not set!")
            success = False
    
    # Check optional variables
    for var in OPTIONAL_WHATSAPP_VARS:
        value = check_env_var(var)
        if value:
            configured_vars.append((var, value))
            logger.info(f"✅ (Optional) {var} is set to: {value}")
    
    # Check if at least one WhatsApp account is fully configured
    if not all(check_env_var(var) for var in ["WHATSAPP_PHONE_ID_0", "WHATSAPP_ACCESS_TOKEN_0"]):
        logger.error("❌ At least one WhatsApp account (index 0) must be fully configured!")
        success = False
    
    # Print summary
    if success:
        logger.info("="*80)
        logger.info("✅ WHATSAPP CONFIGURATION IS COMPLETE")
        logger.info("="*80)
        logger.info(f"Found {len(configured_vars)} configured variables")
    else:
        logger.error("="*80)
        logger.error("❌ WHATSAPP CONFIGURATION IS INCOMPLETE")
        logger.error("="*80)
        
        # Generate .env file example
        env_example = "\n".join([f"{var}=YOUR_VALUE_HERE" for var in missing_vars])
        
        logger.error(f"Please set the following environment variables in your .env file:")
        logger.error("\n" + env_example)
        
        logger.info("\nInstructions to set up WhatsApp API:")
        logger.info("1. Create or log in to a Meta Developer account: https://developers.facebook.com/")
        logger.info("2. Create a WhatsApp Business app")
        logger.info("3. Get your Phone Number ID from the app dashboard")
        logger.info("4. Generate a permanent access token")
        logger.info("5. Add these values to your .env file in the project root directory")
        
    return success
    
def check_env_file():
    """
    Check if .env file exists and load it
    """
    env_path = ".env"
    if os.path.exists(env_path):
        logger.info(f"Found .env file at {os.path.abspath(env_path)}")
        dotenv.load_dotenv(env_path)
        return True
    else:
        logger.warning(f"No .env file found at {os.path.abspath(env_path)}")
        logger.info("Creating a template .env file...")
        
        template = "\n".join([f"{var}=YOUR_VALUE_HERE" for var in REQUIRED_WHATSAPP_VARS])
        with open(env_path, "w") as f:
            f.write(template)
            
        logger.info(f"Created template .env file at {os.path.abspath(env_path)}")
        logger.info("Please edit this file with your actual WhatsApp API credentials")
        return False

if __name__ == "__main__":
    # Check and load .env file
    check_env_file()
    
    # Create Flask app and set up application context
    app = create_app()
    with app.app_context():
        logger.info("="*80)
        logger.info("WHATSAPP CONFIGURATION CHECKER")
        logger.info("="*80)
        
        # Check WhatsApp config
        success = check_whatsapp_config()
        
        if not success:
            sys.exit(1) 