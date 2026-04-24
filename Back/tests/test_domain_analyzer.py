import unittest
from domain.models import Post, VisualAnalysis, TextAnalysis
from domain.analyzers import DomainAnalyzer

class TestDomainAnalyzer(unittest.TestCase):
    def setUp(self):
        self.post = Post(
            post_id="123",
            shortcode="ABC",
            timestamp="2024-01-01T12:00:00Z",
            type="image",
            caption_raw="Hola mundo! #test 📸 @user",
            caption_clean="Hola mundo!",
            hashtags=["test"],
            emojis=["📸"],
            mentions=["user"]
        )

    def test_analyze_text(self):
        self.post.caption_raw = "Hoy es un día feliz! #test 📸 @user"
        analysis = DomainAnalyzer.analyze_text(self.post)
        self.assertIsInstance(analysis, TextAnalysis)
        self.assertEqual(analysis.language_detected, "es")
        self.assertEqual(analysis.sentiment, "positivo")

    def test_calculate_derived_features(self):
        features = DomainAnalyzer.calculate_derived(self.post)
        self.assertEqual(features.caption_length, len(self.post.caption_raw))
        # Note: density depends on words. "Hoy es un día feliz!" has 5 words.
        self.assertGreater(features.emoji_density, 0)

    def test_build_aggregate_features(self):
        # Asegurarse de que el post tenga features derivados calculados
        self.post.derived_features = DomainAnalyzer.calculate_derived(self.post)
        posts = [self.post]
        agg = DomainAnalyzer.build_aggregate_features(posts)
        self.assertIn("posting_frequency_days", agg)
        self.assertIn("language_style", agg)

if __name__ == "__main__":
    unittest.main()
