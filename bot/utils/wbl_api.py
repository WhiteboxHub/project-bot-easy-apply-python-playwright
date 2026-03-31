import os
import requests
from datetime import datetime
from bot.utils.logger import logger

def send_job_activity_log(candidate_id: int, notes: str, job_id: int = 146):
    """
    Sends a bulk job activity log to the Whitebox Learning API.
    """
    base_url = os.getenv("WBL_API_BASE_URL")
    wbl_email = os.getenv("WBL_EMAIL")
    wbl_password = os.getenv("WBL_PASSWORD")
    employee_id = os.getenv("EMPLOYEE_ID")
    
    if not all([base_url, wbl_email, wbl_password, employee_id]):
        logger.warning("WBL API credentials not fully configured in environment. Skipping job activity log.")
        return False
        
    # 1. Login to get token
    login_url = f"{base_url}/login"
    login_data = {
        "username": wbl_email,
        "password": wbl_password
    }
    
    try:
        login_response = requests.post(login_url, data=login_data)
        login_response.raise_for_status()
        token = login_response.json().get("access_token")
        
        if not token:
            logger.error("Failed to retrieve access token from WBL API.", step="wbl_api")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error logging into WBL API: {e}", step="wbl_api")
        return False
        
    # 2. Bulk Create Job Activity Log
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    log_endpoint = f"{base_url}/job_activity_logs/bulk"
    
    # Formatting the payload based on standard job activity log expectations
    payload = {
        "logs": [
            {
                "job_id": job_id,
                "candidate_id": candidate_id,
                "employee_id": int(employee_id) if employee_id and employee_id.isdigit() else employee_id,
                "status": "applied",
                "notes": notes,
                "activity_type": "Auto-Applied via Bot"
            }
        ]
    }
    
    try:
        response = requests.post(log_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Successfully logged metrics to WBL API for candidate {candidate_id}. Notes: {notes}", step="wbl_api")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending log to WBL API: {e}", step="wbl_api")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}", step="wbl_api")
        return False
