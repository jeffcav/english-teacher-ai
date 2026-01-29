"""
Session Manager
Tracks user sessions and maps Telegram users to backend sessions
"""
import json
import os
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Telegram user to backend session mapping"""
    
    def __init__(self, storage_dir: str = "app/feedback_storage"):
        """
        Initialize session manager
        
        Args:
            storage_dir: Directory for storing session data
        """
        self.storage_dir = storage_dir
        self.sessions_file = os.path.join(storage_dir, "telegram_sessions.json")
        
        # Create storage directory if needed
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        
        self.sessions = self._load_sessions()
        logger.info(f"SessionManager initialized with {len(self.sessions)} existing sessions")
    
    def get_or_create_session(self, telegram_user_id: int) -> str:
        """
        Get existing session or create new one for user
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Backend session_id (UUID string)
        """
        if telegram_user_id in self.sessions:
            session = self.sessions[telegram_user_id]
            session['last_activity'] = datetime.now().isoformat()
            self._save_sessions()
            logger.debug(f"Retrieved existing session for user {telegram_user_id}")
            return session['session_id']
        
        # Create new session
        session_id = str(uuid.uuid4())
        self.sessions[telegram_user_id] = {
            'session_id': session_id,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'conversation_turns': 0,
            'state': 'active'
        }
        self._save_sessions()
        logger.info(f"Created new session {session_id} for user {telegram_user_id}")
        return session_id
    
    def get_session(self, telegram_user_id: int) -> Optional[Dict]:
        """
        Get session data for user
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            Session dict or None if not found
        """
        return self.sessions.get(telegram_user_id)
    
    def update_session(self, telegram_user_id: int, **kwargs) -> bool:
        """
        Update session data
        
        Args:
            telegram_user_id: Telegram user ID
            **kwargs: Fields to update (conversation_turns, state, etc.)
            
        Returns:
            True if updated, False if session not found
        """
        if telegram_user_id not in self.sessions:
            return False
        
        session = self.sessions[telegram_user_id]
        session.update(kwargs)
        session['last_activity'] = datetime.now().isoformat()
        self._save_sessions()
        return True
    
    def delete_session(self, telegram_user_id: int) -> bool:
        """
        Delete session (user opt-out/GDPR)
        
        Args:
            telegram_user_id: Telegram user ID
            
        Returns:
            True if deleted, False if not found
        """
        if telegram_user_id not in self.sessions:
            return False
        
        session_id = self.sessions[telegram_user_id]['session_id']
        del self.sessions[telegram_user_id]
        self._save_sessions()
        logger.info(f"Deleted session {session_id} for user {telegram_user_id}")
        return True
    
    def cleanup_expired_sessions(self, timeout_hours: int = 24) -> int:
        """
        Remove inactive sessions
        
        Args:
            timeout_hours: Hours of inactivity before removal
            
        Returns:
            Number of sessions deleted
        """
        cutoff_time = datetime.now() - timedelta(hours=timeout_hours)
        expired_users = []
        
        for user_id, session in self.sessions.items():
            last_activity = datetime.fromisoformat(session['last_activity'])
            if last_activity < cutoff_time:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.sessions[user_id]
        
        if expired_users:
            self._save_sessions()
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")
        
        return len(expired_users)
    
    def get_all_sessions(self) -> Dict:
        """Get all sessions (for monitoring)"""
        return self.sessions.copy()
    
    def get_stats(self) -> Dict:
        """Get session statistics"""
        active_sessions = len(self.sessions)
        total_turns = sum(s.get('conversation_turns', 0) for s in self.sessions.values())
        
        return {
            'active_sessions': active_sessions,
            'total_conversation_turns': total_turns,
            'created_at': datetime.now().isoformat()
        }
    
    def _load_sessions(self) -> Dict:
        """Load sessions from file"""
        if os.path.exists(self.sessions_file):
            try:
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    # Convert string keys to integers
                    return {int(k): v for k, v in data.items()}
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Error loading sessions file: {str(e)}")
                return {}
        return {}
    
    def _save_sessions(self):
        """Save sessions to file"""
        try:
            with open(self.sessions_file, 'w') as f:
                # Convert integer keys to strings for JSON
                data = {str(k): v for k, v in self.sessions.items()}
                json.dump(data, f, indent=2)
        except OSError as e:
            logger.error(f"Error saving sessions file: {str(e)}")
