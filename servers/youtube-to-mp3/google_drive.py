"""
Google Drive upload functionality for MP3 files
Uses OAuth2 credentials from service account or user credentials
"""

import os
import logging
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """
    Get authenticated Google Drive service instance

    Supports two authentication methods:
    1. Service Account (GOOGLE_SERVICE_ACCOUNT_JSON env var)
    2. OAuth2 User Credentials (GOOGLE_DRIVE_CREDENTIALS_JSON env var)

    Returns:
        Google Drive service instance
    """
    creds = None

    # Try service account first
    service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_path and os.path.exists(service_account_path):
        logger.info(f"Using service account credentials: {service_account_path}")
        creds = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=SCOPES
        )
    else:
        # Try user credentials
        credentials_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON")
        if credentials_path and os.path.exists(credentials_path):
            logger.info(f"Using user credentials: {credentials_path}")
            import json
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            creds = Credentials.from_authorized_user_info(creds_data, SCOPES)
        else:
            raise ValueError(
                "No Google Drive credentials found. Set either:\n"
                "  - GOOGLE_SERVICE_ACCOUNT_JSON (path to service account JSON)\n"
                "  - GOOGLE_DRIVE_CREDENTIALS_JSON (path to OAuth2 credentials JSON)"
            )

    # Build and return service
    service = build('drive', 'v3', credentials=creds)
    return service


def upload_to_drive(
    file_path: str,
    folder_id: Optional[str] = None,
    file_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Upload a file to Google Drive

    Args:
        file_path: Path to file to upload
        folder_id: Google Drive folder ID (optional, defaults to root)
        file_name: Custom name for file in Drive (optional, uses filename)

    Returns:
        dict with file_id, web_view_link, and success status
    """
    try:
        service = get_drive_service()

        # Get file name
        if not file_name:
            file_name = os.path.basename(file_path)

        # File metadata
        file_metadata = {
            'name': file_name,
            'mimeType': 'audio/mpeg'
        }

        # Add parent folder if specified
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # Upload file
        media = MediaFileUpload(
            file_path,
            mimetype='audio/mpeg',
            resumable=True
        )

        logger.info(f"Uploading {file_name} to Google Drive...")

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, webContentLink, size'
        ).execute()

        logger.info(f"Upload successful! File ID: {file.get('id')}")

        return {
            'success': True,
            'file_id': file.get('id'),
            'name': file.get('name'),
            'web_view_link': file.get('webViewLink'),
            'web_content_link': file.get('webContentLink'),
            'size': int(file.get('size', 0))
        }

    except HttpError as error:
        logger.error(f"Google Drive API error: {error}")
        raise ValueError(f"Failed to upload to Google Drive: {error}")
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {str(e)}")
        raise ValueError(f"Failed to upload to Google Drive: {str(e)}")


def get_or_create_folder(folder_name: str, parent_id: Optional[str] = None) -> str:
    """
    Get existing folder by name or create if doesn't exist

    Args:
        folder_name: Name of folder
        parent_id: Parent folder ID (optional, defaults to root)

    Returns:
        Folder ID
    """
    try:
        service = get_drive_service()

        # Search for existing folder
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"

        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = results.get('files', [])

        if files:
            # Folder exists
            logger.info(f"Found existing folder: {folder_name} (ID: {files[0]['id']})")
            return files[0]['id']
        else:
            # Create folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }

            if parent_id:
                file_metadata['parents'] = [parent_id]

            folder = service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            logger.info(f"Created new folder: {folder_name} (ID: {folder.get('id')})")
            return folder.get('id')

    except Exception as e:
        logger.error(f"Error getting/creating folder: {str(e)}")
        raise ValueError(f"Failed to get/create folder: {str(e)}")


def is_drive_configured() -> bool:
    """
    Check if Google Drive credentials are configured

    Returns:
        True if credentials are configured, False otherwise
    """
    service_account_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    credentials_path = os.environ.get("GOOGLE_DRIVE_CREDENTIALS_JSON")

    if service_account_path and os.path.exists(service_account_path):
        return True
    if credentials_path and os.path.exists(credentials_path):
        return True

    return False
