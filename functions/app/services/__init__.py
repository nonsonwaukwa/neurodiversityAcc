# Services package 

# Progress Report Service
from app.services.progress_report import ProgressReportService

_progress_service = None

def get_progress_service():
    """
    Get the progress report service
    
    Returns:
        ProgressReportService: The progress report service
    """
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressReportService()
    return _progress_service 