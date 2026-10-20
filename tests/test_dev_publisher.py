"""Publisher regression tests; API calls are mocked, no DEV credentials needed."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import publish_to_dev as publisher


class TestPublisher(unittest.TestCase):
    def test_published_date_counts_when_boolean_is_missing(self):
        self.assertTrue(publisher._is_published({"published_at": "2026-10-20T02:49:34Z"}))
        self.assertTrue(publisher._is_published({"published": True}))
        self.assertFalse(publisher._is_published({"published_at": None}))

    def test_challenge_tags_are_read_from_both_dev_shapes(self):
        self.assertTrue(publisher._has_challenge_tags(
            {"tags": "devchallenge, hf26challenge, opensource, python"}
        ))
        self.assertTrue(publisher._has_challenge_tags(
            {"tag_list": ["devchallenge", "hf26challenge", "opensource"]}
        ))
        self.assertFalse(publisher._has_challenge_tags({"tag_list": ["python"]}))

    def _published(self):
        return {
            "id": 123, "title": publisher.ARTICLE_TITLE,
            "url": "https://dev.to/infraopsx/quietops-example-abc",
            "published_at": "2026-10-20T02:49:34Z",
            "tag_list": ["devchallenge", "hf26challenge", "opensource", "python"],
        }

    def test_published_article_same_body_is_not_modified(self):
        article = self._published()
        with patch.object(publisher, "find_existing", return_value=article):
            with patch.object(publisher, "api_call", return_value={"body_markdown": "body"}) as api:
                self.assertEqual(publisher.publish("fake-key", "body"), article["url"])
                api.assert_called_once_with("/articles/123", "fake-key")

    def test_existing_published_article_is_updated_in_place_when_body_changes(self):
        article = self._published()
        with patch.object(publisher, "find_existing", side_effect=[article, article]):
            with patch.object(publisher, "api_call", side_effect=[
                {"body_markdown": "outdated article"},
                {"id": 123},
                {"body_markdown": "body with live link"},
            ]) as api:
                self.assertEqual(publisher.publish("fake-key", "body with live link"), article["url"])
                self.assertEqual(api.call_count, 3)
                self.assertEqual(api.call_args_list[1].args[0], "/articles/123")
                self.assertEqual(api.call_args_list[1].kwargs["method"], "PUT")
                self.assertEqual(api.call_args_list[1].kwargs["payload"]["article"]["body_markdown"], "body with live link")

    def test_existing_draft_is_updated_with_correct_tags(self):
        draft = {"id": 123, "title": publisher.ARTICLE_TITLE, "published_at": None}
        published = self._published()
        with patch.object(publisher, "find_existing", side_effect=[draft, published]):
            with patch.object(publisher, "api_call", side_effect=[
                {"id": 123}, {"body_markdown": "body"},
            ]) as api:
                self.assertEqual(publisher.publish("fake-key", "body"), published["url"])
                self.assertEqual(api.call_args_list[0].args[0], "/articles/123")
                self.assertEqual(api.call_args_list[0].kwargs["method"], "PUT")
                fields = api.call_args_list[0].kwargs["payload"]["article"]
                self.assertIs(fields["published"], True)
                self.assertEqual(fields["tags"], "devchallenge, hf26challenge, opensource, python")

    def test_create_verifies_publication_without_published_boolean(self):
        article = self._published()
        with patch.object(publisher, "find_existing", side_effect=[None, article]):
            with patch.object(publisher, "api_call", side_effect=[
                {"id": 123}, {"body_markdown": "body"},
            ]) as api:
                self.assertEqual(publisher.publish("fake-key", "body"), article["url"])
                self.assertEqual(api.call_args_list[0].args[0], "/articles")
                self.assertEqual(api.call_args_list[0].kwargs["method"], "POST")

    def test_remote_body_mismatch_fails_after_update(self):
        article = self._published()
        with patch.object(publisher, "find_existing", side_effect=[article, article]):
            with patch.object(publisher, "api_call", side_effect=[
                {"body_markdown": "old"}, {"id": 123}, {"body_markdown": "still old"}
            ]):
                with self.assertRaisesRegex(RuntimeError, "body does not match"):
                    publisher.publish("fake-key", "new body")

    def test_missing_remote_article_body_stops_without_duplicate(self):
        article = self._published()
        with patch.object(publisher, "find_existing", return_value=article):
            with patch.object(publisher, "api_call", return_value={"id": 123}) as api:
                with self.assertRaisesRegex(RuntimeError, "body_markdown"):
                    publisher.publish("fake-key", "new body")
                api.assert_called_once()



if __name__ == "__main__":
    unittest.main()
