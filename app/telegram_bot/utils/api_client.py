"""
API Client for Backend Communication
Handles all HTTP requests to the PhonicFlow backend
"""
import requests
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class APIClient:
    """Backend API communication client with retry logic"""
    
    def __init__(self, backend_url: str, timeout: int = 30):
        """
        Initialize API client
        
        Args:
            backend_url: Base URL of backend API (e.g., http://localhost:8000)
            timeout: Request timeout in seconds
        """
        self.backend_url = backend_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
    
    def process_audio(self, session_id: str, audio_bytes: bytes) -> Dict[str, Any]:
        """
        Submit audio to backend for processing
        
        Args:
            session_id: Unique session identifier
            audio_bytes: WAV audio data
            
        Returns:
            Response containing transcript, feedback, and audio paths
            
        Raises:
            requests.RequestException: If request fails
        """
        try:
            endpoint = f"{self.backend_url}/process"
            files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
            params = {"session_id": session_id}
            
            logger.info(f"Submitting audio for session {session_id}")
            response = self.session.post(
                endpoint,
                files=files,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Audio processed successfully for session {session_id}")
                return data
            else:
                logger.error(f"Backend error {response.status_code}: {response.text}")
                raise requests.RequestException(
                    f"Backend returned {response.status_code}"
                )
        
        except requests.Timeout:
            logger.error(f"Timeout processing audio for session {session_id}")
            raise
        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            raise
    
    def get_conversation_history(self, session_id: str) -> list:
        """
        Retrieve conversation history
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            List of conversation turns
        """
        try:
            endpoint = f"{self.backend_url}/conversation/{session_id}"
            
            logger.info(f"Fetching history for session {session_id}")
            response = self.session.get(
                endpoint,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                history = data.get("history", [])
                logger.info(f"Retrieved {len(history)} history items")
                return history
            else:
                logger.warning(f"Failed to get history: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"Error fetching history: {str(e)}")
            return []
    
    def get_feedback_audio(self, session_id: str, audio_type: str = "coaching") -> Optional[bytes]:
        """
        Retrieve synthesized audio feedback
        
        Args:
            session_id: Unique session identifier
            audio_type: Type of audio ("coaching" or "conversational")
            
        Returns:
            Audio WAV bytes or None if unavailable
        """
        try:
            endpoint = f"{self.backend_url}/audio/{session_id}"
            params = {"audio_type": audio_type}
            
            logger.info(f"Fetching {audio_type} audio for session {session_id}")
            response = self.session.get(
                endpoint,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                logger.info(f"Retrieved {audio_type} audio ({len(response.content)} bytes)")
                return response.content
            else:
                logger.warning(f"No {audio_type} audio available")
                return None
        
        except Exception as e:
            logger.error(f"Error fetching audio: {str(e)}")
            return None
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear conversation session
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            endpoint = f"{self.backend_url}/conversation/{session_id}"
            
            logger.info(f"Clearing session {session_id}")
            response = self.session.delete(
                endpoint,
                timeout=self.timeout
            )
            
            return response.status_code == 200
        
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return False
    
    def health_check(self) -> bool:
        """
        Check backend health status
        
        Returns:
            True if backend is accessible, False otherwise
        """
        try:
            endpoint = f"{self.backend_url}/docs"
            response = self.session.get(
                endpoint,
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
