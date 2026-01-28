"""
Example usage of PhonicFlow API.
Demonstrates how to interact with the backend programmatically.
"""
import requests
import json
from pathlib import Path


class PhonicFlowClient:
    """Client for interacting with PhonicFlow API."""
    
    def __init__(self, api_url="http://localhost:8000"):
        """Initialize the client with API URL."""
        self.api_url = api_url
    
    def health_check(self):
        """Check API health."""
        response = requests.get(f"{self.api_url}/health")
        return response.json()
    
    def process_audio(self, audio_file_path, session_id=None):
        """
        Process audio file and get coaching feedback.
        
        Args:
            audio_file_path: Path to audio file
            session_id: Optional session identifier
            
        Returns:
            Dictionary with transcript, feedback, and audio path
        """
        if not Path(audio_file_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        with open(audio_file_path, 'rb') as f:
            files = {'file': f}
            params = {}
            if session_id:
                params['session_id'] = session_id
            
            response = requests.post(
                f"{self.api_url}/process",
                files=files,
                params=params,
                timeout=60
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    def get_audio(self, session_id, output_path=None):
        """
        Retrieve feedback audio file.
        
        Args:
            session_id: Session identifier
            output_path: Optional path to save audio (default: session_id.mp3)
            
        Returns:
            Path to audio file
        """
        if output_path is None:
            output_path = f"{session_id}.mp3"
        
        response = requests.get(f"{self.api_url}/audio/{session_id}")
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            return output_path
        else:
            raise Exception(f"Failed to get audio: {response.status_code}")
    
    def get_config(self):
        """Get current configuration."""
        response = requests.get(f"{self.api_url}/config")
        return response.json()
    
    def update_config(self, whisper_model=None, llm_name=None, tts_voice=None):
        """Update configuration."""
        config = {}
        if whisper_model:
            config['whisper_model'] = whisper_model
        if llm_name:
            config['llm_name'] = llm_name
        if tts_voice:
            config['tts_voice'] = tts_voice
        
        response = requests.post(f"{self.api_url}/config", json=config)
        return response.json()


# Example usage
if __name__ == "__main__":
    client = PhonicFlowClient()
    
    # Check health
    print("Checking API health...")
    health = client.health_check()
    print(json.dumps(health, indent=2))
    
    # Example: Process a test audio file
    # (You would need an actual audio file)
    # result = client.process_audio("test_audio.wav", "my_session_001")
    # print(json.dumps(result, indent=2))
    # 
    # # Download the feedback audio
    # audio_file = client.get_audio("my_session_001", "feedback.mp3")
    # print(f"Audio saved to: {audio_file}")
