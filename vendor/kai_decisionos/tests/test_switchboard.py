import unittest
from unittest.mock import patch, MagicMock
import time

from apps.switchboard import switch

class TestSwitchboard(unittest.TestCase):

    def setUp(self): 
        # Mock settings
        self.mock_settings = MagicMock()
        self.mock_settings.routes_path = "dummy_routes.yaml"
        
        # Mock routes file content
        self.routes_content = """
        default:
            model: gpt-4
            max_cost: 0.5
            max_latency: 5
            fallback_model: local-model
        """
        
    @patch("apps.switchboard.switch.settings")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    def test_cost_fallback(self, mock_read_text, mock_exists, mock_settings):
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_exists.return_value = True
        mock_read_text.return_value = self.routes_content
        
        # Act
        meta = switch.choose_route("default", budgets={"cost": 0.6})
        
        # Assert
        self.assertEqual(meta["chosen_model"], "local-model")

    @patch("apps.switchboard.switch.settings")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.read_text")
    @patch("adapters.openai.send_request")
    def test_timeout_fallback(self, mock_openai_send, mock_read_text, mock_exists, mock_settings):
        # Arrange
        mock_settings.return_value = self.mock_settings
        mock_exists.return_value = True
        mock_read_text.return_value = self.routes_content
        
        # Simulate a slow response from OpenAI
        def slow_response(*args, **kwargs):
            time.sleep(6)
            return {"usage": {}}
            
        mock_openai_send.side_effect = slow_response
        
        meta = switch.choose_route("default")

        # Act
        _, meta = switch.execute_request("test prompt", meta)
        
        # Assert
        self.assertEqual(meta["fallback_reason"], "latency")

if __name__ == "__main__":
    unittest.main()
