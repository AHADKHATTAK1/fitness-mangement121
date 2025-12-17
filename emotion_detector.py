"""
LIGHTWEIGHT Emotion Detection 
Fast & responsive - no heavy dependencies!
"""

import os
import base64
from PIL import Image
import io

# Simple emotion mapping (can be enhanced later)
EMOTIONS_MAP = {
    'happy': '😊',
    'sad': '😢', 
    'angry': '😠',
    'surprise': '😲',
    'fear': '😨',
    'disgust': '🤢',
    'neutral': '😐'
}

class EmotionDetector:
    """Lightweight emotion detection - placeholder for future ML"""
    
    def __init__(self):
        """Initialize lightweight detector"""
        self.available = True  # Always available
        self.emotions = list(EMOTIONS_MAP.keys())
    
    def is_available(self):
        """Check if emotion detection is available"""
        return True
    
    def detect_emotion_from_image(self, image_path):
        """
        Detect emotion from image (simplified version)
        Returns neutral for now - can add ML model later
        
        Args:
            image_path: Path to image file
            
        Returns:
            dict: {'emotion': 'neutral', 'confidence': 1.0}
        """
        # For now, return neutral emotion
        # This keeps system FAST and responsive
        # Can be upgraded to real ML later
        return {
            'emotion': 'neutral',
            'confidence': 1.0,
            'all_emotions': {'neutral': 100}
        }
    
    def detect_emotion_from_base64(self, base64_image):
        """
        Detect emotion from base64 (simplified)
        
        Args:
            base64_image: Base64 string
            
        Returns:
            dict: Emotion data
        """
        # Fast response - no processing needed
        return self.detect_emotion_from_image(None)
    
    def get_emoji(self, emotion):
        """Get emoji for emotion"""
        return EMOTIONS_MAP.get(emotion.lower(), '😐')
    
    def get_message(self, emotion):
        """Get encouraging message"""
        messages = {
            'happy': 'Great to see you! Have an amazing workout! 💪',
            'sad': 'Hope your workout lifts your spirits! 💪',
            'angry': 'Channel that energy! 💪',
            'surprise': 'Ready for a great session! 💪',
            'fear': 'You got this! 💪',
            'disgust': 'Let\'s turn that around! 💪',
            'neutral': 'Let\'s get pumped! Have a great workout! 💪'
        }
        return messages.get(emotion.lower(), 'Have a great workout! 💪')

# Note: To enable real emotion detection later:
# 1. Install: pip install fer
# 2. Uncomment advanced code below
# 3. System will auto-upgrade to ML detection

"""
# ADVANCED EMOTION DETECTION (Optional - Uncomment to enable)
try:
    from fer import FER
    detector = FER(mtcnn=True)
    ML_AVAILABLE = True
except:
    ML_AVAILABLE = False

# Replace detect_emotion_from_image with:
def detect_emotion_advanced(image_path):
    if ML_AVAILABLE:
        result = detector.detect_emotions(image_path)
        if result:
            emotions = result[0]['emotions']
            dominant = max(emotions, key=emotions.get)
            return {
                'emotion': dominant,
                'confidence': emotions[dominant],
                'all_emotions': emotions
            }
    return {'emotion': 'neutral', 'confidence': 1.0}
"""

