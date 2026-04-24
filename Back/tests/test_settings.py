import unittest
import os
from config.settings import Settings

class TestSettings(unittest.TestCase):
    def test_settings_load(self):
        # Settings is a singleton, but we can check if it loaded some defaults or envs
        from config.settings import settings
        self.assertIsInstance(settings.posts_limit, int)
        self.assertIsInstance(settings.playwright_headless, bool)
        
    def test_validate_missing_cookies(self):
        s = Settings(target_account="", ig_session_id="")
        with self.assertRaises(ValueError):
            s.validate()

if __name__ == "__main__":
    unittest.main()
