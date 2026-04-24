import unittest
from unittest.mock import MagicMock, patch
from infrastructure.ai.groq_client import GroqClient

class TestGroqClient(unittest.TestCase):
    def setUp(self):
        self.api_key = "test_key"
        self.client = GroqClient(api_key=self.api_key)

    @patch("infrastructure.ai.groq_client.Groq")
    @patch("infrastructure.ai.groq_client.httpx.get")
    def test_analyze_post_visual(self, mock_get, mock_groq_class):
        # Setup mocks
        mock_groq_instance = MagicMock()
        mock_groq_class.return_value = mock_groq_instance
        self.client.client = mock_groq_instance
        
        mock_get.return_value.content = b"fake_image_data"
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = '{"scene_tags": ["test"], "confidence": 0.9}'
        mock_groq_instance.chat.completions.create.return_value = mock_completion

        # Execute
        result = self.client.analyze_post_visual("http://example.com/img.jpg", "test caption")
        
        # Verify
        self.assertEqual(result["scene_tags"], ["test"])
        self.assertEqual(result["confidence"], 0.9)
        mock_groq_instance.chat.completions.create.assert_called_once()

    @patch("infrastructure.ai.groq_client.Groq")
    def test_analyze_personality_ocean(self, mock_groq_class):
        mock_groq_instance = MagicMock()
        self.client.client = mock_groq_instance
        
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = '{"openness": {"score": 0.8}}'
        mock_groq_instance.chat.completions.create.return_value = mock_completion

        result = self.client.analyze_personality_ocean("bio test", [{"caption_raw": "post test"}])
        
        self.assertEqual(result["openness"]["score"], 0.8)

if __name__ == "__main__":
    unittest.main()
