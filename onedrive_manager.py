"""
OneDrive manager for official lab sheet generator account
Handles file uploads and share link generation
"""

import os
import requests
import json
from pathlib import Path


class OneDriveManager:
    """Manages OneDrive uploads for official account."""
    
    def __init__(self, client_id=None, client_secret=None, refresh_token=None):
        """Initialize OneDrive manager."""
        self.client_id = client_id or os.getenv('ONEDRIVE_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('ONEDRIVE_CLIENT_SECRET')
        self.refresh_token = refresh_token or os.getenv('ONEDRIVE_REFRESH_TOKEN')
        
        self.access_token = None
        self.enabled = bool(self.client_id and self.client_secret and self.refresh_token)
    
    def get_access_token(self):
        """Get fresh access token using refresh token."""
        if not self.enabled:
            return None
        
        try:
            token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token',
                'scope': 'https://graph.microsoft.com/Files.ReadWrite offline_access'
            }
            
            response = requests.post(token_url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            return self.access_token
            
        except Exception as e:
            print(f"Error getting access token: {e}")
            return None
    
    def upload_file(self, file_path, student_id):
        """
        Upload file to OneDrive in student's folder.
        
        Args:
            file_path: Path to file to upload
            student_id: Student ID for folder organization
            
        Returns:
            dict with success status and share link
        """
        if not self.enabled:
            return {'success': False, 'error': 'OneDrive not configured'}
        
        try:
            # Get access token
            token = self.get_access_token()
            if not token:
                return {'success': False, 'error': 'Failed to get access token'}
            
            # Get file info
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Create folder structure: LabSheets/{student_id}/
            folder_path = f"/LabSheets/{student_id}"
            
            # Ensure folder exists
            self._ensure_folder_exists(folder_path, token)
            
            # Upload file
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{folder_path}/{file_name}:/content"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/octet-stream'
            }
            
            with open(file_path, 'rb') as f:
                response = requests.put(upload_url, headers=headers, data=f)
            
            if response.status_code not in [200, 201]:
                return {'success': False, 'error': f'Upload failed: {response.text}'}
            
            # Get file ID
            file_data = response.json()
            file_id = file_data['id']
            
            # Create share link
            share_link = self._create_share_link(file_id, token)
            
            return {
                'success': True,
                'file_id': file_id,
                'file_name': file_name,
                'share_link': share_link,
                'folder': folder_path
            }
            
        except Exception as e:
            print(f"Error uploading to OneDrive: {e}")
            return {'success': False, 'error': str(e)}
    
    def _ensure_folder_exists(self, folder_path, token):
        """Ensure folder exists, create if not."""
        try:
            # Split path
            parts = [p for p in folder_path.split('/') if p]
            
            current_path = ''
            for part in parts:
                current_path += f'/{part}'
                
                # Try to get folder
                check_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{current_path}"
                headers = {'Authorization': f'Bearer {token}'}
                
                response = requests.get(check_url, headers=headers)
                
                if response.status_code == 404:
                    # Folder doesn't exist, create it
                    parent_path = current_path.rsplit('/', 1)[0] or ''
                    create_url = f"https://graph.microsoft.com/v1.0/me/drive/root:{parent_path}:/children"
                    
                    data = {
                        'name': part,
                        'folder': {},
                        '@microsoft.graph.conflictBehavior': 'rename'
                    }
                    
                    headers = {
                        'Authorization': f'Bearer {token}',
                        'Content-Type': 'application/json'
                    }
                    
                    requests.post(create_url, headers=headers, json=data)
            
            return True
            
        except Exception as e:
            print(f"Error ensuring folder exists: {e}")
            return False
    
    def _create_share_link(self, file_id, token):
        """Create shareable link for file."""
        try:
            share_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/createLink"
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'type': 'view',
                'scope': 'anonymous'
            }
            
            response = requests.post(share_url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                link_data = response.json()
                return link_data['link']['webUrl']
            
            return None
            
        except Exception as e:
            print(f"Error creating share link: {e}")
            return None


# Singleton instance
_onedrive_manager = None

def get_onedrive_manager():
    """Get OneDrive manager singleton."""
    global _onedrive_manager
    if _onedrive_manager is None:
        _onedrive_manager = OneDriveManager()
    return _onedrive_manager
