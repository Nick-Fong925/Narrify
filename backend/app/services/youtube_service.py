import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from app.config import settings
from app.utils.logger import logger


# YouTube API scopes
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly',
]


class YouTubeService:
    """Service for uploading videos to YouTube"""
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
    
    def authenticate(self) -> None:
        """Authenticate with YouTube API using OAuth 2.0."""
        token_file = Path(settings.youtube_token_file)
        credentials_file = Path(settings.youtube_client_secrets_file)
        
        # Check if we have valid saved credentials
        if token_file.exists():
            with open(token_file, 'rb') as token:
                self.credentials = pickle.load(token)
        
        # If no valid credentials, get new ones
        if not self.credentials or not self.credentials.valid:
            if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                # Refresh expired credentials
                logger.info("Refreshing YouTube OAuth credentials")
                self.credentials.refresh(Request())
            else:
                # Get new credentials via OAuth flow
                if not credentials_file.exists():
                    raise FileNotFoundError(
                        f"YouTube credentials file not found: {credentials_file}\n"
                        "Download from Google Cloud Console: https://console.cloud.google.com/"
                    )
                
                logger.info("Starting YouTube OAuth flow - browser will open")
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_file),
                    SCOPES
                )
                self.credentials = flow.run_local_server(port=0)
            
            # Save credentials for future use
            token_file.parent.mkdir(parents=True, exist_ok=True)
            with open(token_file, 'wb') as token:
                pickle.dump(self.credentials, token)
            logger.info("YouTube OAuth credentials saved")
        
        # Build YouTube API client
        self.youtube = build('youtube', 'v3', credentials=self.credentials)
        logger.info("YouTube API client initialized")
    
    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "24",
        privacy_status: str = "public",
        publish_at: Optional[datetime] = None,
    ) -> Optional[str]:
        if not self.youtube:
            self.authenticate()
        
        video_file = Path(video_path)
        if not video_file.exists():
            logger.error(f"Video file not found: {video_path}")
            return None
        
        # Add #shorts to title
        full_title = f"{title}{settings.youtube.title_suffix}"
        
        # Combine default tags with provided tags
        all_tags = list(settings.youtube.default_tags)
        if tags:
            all_tags.extend(tags)
        
        # Prepare video metadata
        status_body: Dict[str, Any] = {
            'selfDeclaredMadeForKids': False,
        }
        if publish_at is not None:
            status_body['privacyStatus'] = 'private'
            status_body['publishAt'] = publish_at.isoformat()
        else:
            status_body['privacyStatus'] = privacy_status

        body = {
            'snippet': {
                'title': full_title,
                'description': description,
                'tags': all_tags,
                'categoryId': category_id
            },
            'status': status_body,
        }
        
        # Create media upload object
        media = MediaFileUpload(
            str(video_file),
            chunksize=1024*1024,  # 1MB chunks
            resumable=True
        )
        
        try:
            logger.info(f"Uploading video to YouTube: {full_title}")
            
            # Execute upload
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.debug(f"Upload progress: {progress}%")
            
            video_id = response['id']
            logger.info(
                f"YouTube upload successful",
                video_id=video_id,
                url=f"https://youtube.com/shorts/{video_id}"
            )
            
            return video_id
            
        except Exception as e:
            logger.error(f"YouTube upload failed", exception=e)
            return None
    
    def delete_video(self, video_id: str) -> bool:
        if not self.youtube:
            self.authenticate()
        
        try:
            self.youtube.videos().delete(id=video_id).execute()
            logger.info(f"YouTube video deleted: {video_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete YouTube video: {video_id}", exception=e)
            return False
    
    def get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        if not self.youtube:
            self.authenticate()
        
        try:
            request = self.youtube.videos().list(
                part='snippet,status,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                return response['items'][0]
            return None
            
        except Exception as e:
            logger.error(f"Failed to get YouTube video info: {video_id}", exception=e)
            return None


# Global YouTube service instance
youtube_service = YouTubeService()
