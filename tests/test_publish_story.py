import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import publish  # noqa: E402


class StoryTest(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.orig = (publish.graph, publish.wait_ready)

        def fake_graph(method, path, token, **p):
            self.calls.append((method, path, p))
            if method == "GET":
                return {"access_token": "x"}
            return {"id": f"id{len(self.calls)}"}

        publish.graph = fake_graph
        publish.wait_ready = lambda *a, **k: None

    def tearDown(self):
        publish.graph, publish.wait_ready = self.orig

    def test_instagram_test_modus_veroeffentlicht_nicht(self):
        r = publish.instagram_stories("ig", "t", ["u1", "u2"], False)
        self.assertEqual(len(r["stories"]), 2)
        self.assertFalse(any(c[1].endswith("media_publish") for c in self.calls))
        self.assertTrue(all(c[2].get("media_type") == "STORIES" for c in self.calls))

    def test_instagram_publish(self):
        publish.instagram_stories("ig", "t", ["u1"], True)
        self.assertTrue(any(c[1].endswith("media_publish") for c in self.calls))

    def test_facebook_test_und_publish(self):
        publish.facebook_stories("pg", "t", ["u1"], False)
        self.assertFalse(any(c[1].endswith("photo_stories") for c in self.calls))
        publish.facebook_stories("pg", "t", ["u1"], True)
        self.assertTrue(any(c[1].endswith("photo_stories") for c in self.calls))

    def test_instagram_videostory(self):
        r = publish.instagram_story_videos("ig", "t", ["v1", "v2"], False)
        self.assertEqual(len(r["stories"]), 2)
        self.assertTrue(all(c[2].get("video_url") for c in self.calls if c[0] == "POST"))
        self.assertFalse(any(c[1].endswith("media_publish") for c in self.calls))

    def test_facebook_videostory_test_ohne_finish(self):
        def g(method, path, token, **p):
            self.calls.append((method, path, p))
            if method == "GET" and path == "pg":
                return {"access_token": "x"}
            if method == "GET":
                return {"status": {"video_status": "ready"}}
            if p.get("upload_phase") == "start":
                return {"video_id": "v1", "upload_url": "https://rupload.facebook.com/video-upload/v1"}
            return {"id": "s1"}
        publish.graph = g
        orig_http = publish.http
        publish.http = lambda *a, **k: (200, b'{"success": true}', {})
        try:
            publish.facebook_story_videos("pg", "t", ["u"], False)
            self.assertFalse(any(c[2].get("upload_phase") == "finish" for c in self.calls))
            publish.facebook_story_videos("pg", "t", ["u"], True)
            self.assertTrue(any(c[2].get("upload_phase") == "finish" for c in self.calls))
        finally:
            publish.http = orig_http


if __name__ == "__main__":
    unittest.main()
