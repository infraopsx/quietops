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

    def test_published_article_is_not_posted_twice(self):
        article = {
            "id": 123, "title": publisher.ARTICLE_TITLE,
            "url": "https://dev.to/infraopsx/quietops-example-abc",
            "published_at": "2026-10-20T02:49:34Z",
            "tag_list": ["devchallenge", "hf26challenge"],
        }
        with patch.object(publisher, "find_existing", return_value=article):
            with patch.object(publisher, "api_call") as api:
                self.assertEqual(publisher.publish("fake-key", "body"), article["url"])
                api.assert_not_called()

    def test_existing_draft_is_updated_with_correct_tags(self):
        draft = {"id": 123, "title": publisher.ARTICLE_TITLE, "published_at": None}
        published = {
            **draft, "published_at": "2026-10-20T02:49:34Z",
            "url": "https://dev.to/infraopsx/quietops-example-abc",
            "tag_list": ["devchallenge", "hf26challenge", "opensource", "python"],
        }
        with patch.object(publisher, "find_existing", side_effect=[draft, published]):
            with patch.object(publisher, "api_call", return_value={"id": 123}) as api:
                self.assertEqual(publisher.publish("fake-key", "body"), published["url"])
                args, kwargs = api.call_args
                self.assertEqual(args[0], "/articles/123")
                self.assertEqual(kwargs["method"], "PUT")
                fields = kwargs["payload"]["article"]
                self.assertIs(fields["published"], True)
                self.assertEqual(fields["tags"], "devchallenge, hf26challenge, opensource, python")

    def test_create_verifies_publication_without_published_field(self):
        new = {
            "id": 123, "title": publisher.ARTICLE_TITLE,
            "published_at": "2026-10-20T02:49:34Z",
            "tag_list": ["devchallenge", "hf26challenge"],
            "url": "https://dev.to/infraopsx/quietops-example-abc",
        }
        with patch.object(publisher, "find_existing", side_effect=[None, new]):
            with patch.object(publisher, "api_call", return_value={"id": 123}) as api:
                self.assertEqual(publisher.publish("fake-key", "body"), new["url"])
                self.assertEqual(api.call_args.args[0], "/articles")
                self.assertEqual(api.call_args.kwargs["method"], "POST")


if __name__ == "__main__":
    unittest.main()
