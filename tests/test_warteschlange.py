import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import publish  # noqa: E402
import warteschlange as w  # noqa: E402


class FakeRest:
    """Minimaler In-Memory-Ersatz für die Tabelle publish_queue."""
    def __init__(self, rows):
        self.rows = rows

    def call(self, method, path, body=None, params=None, prefer=None):
        params = params or {}
        def match(r):
            for k, v in params.items():
                if k in ("select", "order", "limit"):
                    continue
                op, _, val = v.partition(".")
                x = str(r.get(k))
                if op == "eq" and x != val:
                    return False
                if op == "lte" and not r.get(k) <= val:
                    return False
                if op == "lt" and not r.get(k) < val:
                    return False
            return True
        hit = [r for r in self.rows if match(r)]
        if method == "GET":
            return [dict(r) for r in hit]
        if method == "PATCH":
            for r in hit:
                r.update(body)
            return [dict(r) for r in hit] if prefer and "representation" in prefer else None


class Basis(unittest.TestCase):
    def setUp(self):
        self.orig = {n: getattr(publish, n) for n in ("instagram", "facebook", "instagram_reel", "facebook_video")}
        self.orig_storage = publish.Storage
        self.log = []
        self.fb_fail = False
        publish.instagram = lambda *a, **k: self.log.append("ig") or {"veroeffentlicht": True}
        def fb(*a, **k):
            if self.fb_fail:
                raise publish.Fehler("Meta: kaputt")
            self.log.append("fb")
            return {"post_id": "1"}
        publish.facebook = fb
        class S:
            paths = []
            def cleanup(s):
                self.log.append("cleanup")
        publish.Storage = S
        w.ENV.update({"IG_USER_ID": "ig", "FB_PAGE_ID": "pg", "META_SYSTEM_TOKEN": "tok"})
        self.orig_rest = w.Rest

    def tearDown(self):
        for n, f in self.orig.items():
            setattr(publish, n, f)
        publish.Storage = self.orig_storage
        w.Rest = self.orig_rest

    def row(self, **k):
        r = {"id": 1, "slot": "T04-K", "kind": "karussell", "publish_at": "2026-11-19T05:45:00Z", "caption": "c",
             "urls": ["u1", "u2"], "cover_url": None, "targets": ["ig", "fb"], "paths": ["p"], "status": "pending",
             "attempts": 0, "result": {}, "error": None, "updated_at": "2026-11-18T10:00:00Z"}
        r.update(k)
        return r


class RunTest(Basis):
    def run_with(self, rows, now):
        w.Rest = lambda: FakeRest(rows)
        return w.cmd_run(now)

    def test_faellig_wird_veroeffentlicht(self):
        rows = [self.row()]
        self.assertEqual(self.run_with(rows, "2026-11-19T05:50:00Z"), 0)
        self.assertEqual(rows[0]["status"], "done")
        self.assertEqual(self.log, ["ig", "fb", "cleanup"])

    def test_nicht_faellig_bleibt_stehen(self):
        rows = [self.row()]
        self.run_with(rows, "2026-11-19T05:00:00Z")
        self.assertEqual(rows[0]["status"], "pending")
        self.assertEqual(self.log, [])

    def test_fehler_bei_facebook_wiederholt_nur_facebook(self):
        rows = [self.row()]
        self.fb_fail = True
        self.assertEqual(self.run_with(rows, "2026-11-19T05:50:00Z"), 1)
        self.assertEqual(rows[0]["status"], "pending")
        self.assertIn("instagram", rows[0]["result"])
        self.fb_fail = False
        self.log.clear()
        self.run_with(rows, "2026-11-19T06:00:00Z")
        self.assertEqual(rows[0]["status"], "done")
        self.assertEqual(self.log, ["fb", "cleanup"])  # Instagram nicht noch einmal

    def test_nach_drei_versuchen_error(self):
        rows = [self.row()]
        self.fb_fail = True
        for i in range(3):
            self.run_with(rows, f"2026-11-19T05:{50 + i}:00Z")
        self.assertEqual(rows[0]["status"], "error")

    def test_verpasst_wird_nicht_gepostet(self):
        rows = [self.row()]
        self.assertEqual(self.run_with(rows, "2026-11-19T12:00:00Z"), 1)
        self.assertEqual(rows[0]["status"], "error")
        self.assertEqual(self.log, [])

    def test_haengender_lauf_wird_gemeldet(self):
        rows = [self.row(status="running", updated_at="2026-11-19T05:00:00Z", publish_at="2026-11-19T04:00:00Z")]
        self.assertEqual(self.run_with(rows, "2026-11-19T05:50:00Z"), 1)
        self.assertEqual(rows[0]["status"], "error")
        self.assertEqual(self.log, [])


class ZeitTest(unittest.TestCase):
    def test_winterzeit(self):
        self.assertEqual(w.zurich_to_utc("2026-11-19 06:45"), "2026-11-19T05:45:00Z")

    def test_sommerzeit(self):
        self.assertEqual(w.zurich_to_utc("2026-07-01 06:45"), "2026-07-01T04:45:00Z")


if __name__ == "__main__":
    unittest.main()
