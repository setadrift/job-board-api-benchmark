import unittest

from benchmark import duplicate_count, extract_records, normalize_record, percentage


class NormalizationTests(unittest.TestCase):
    def test_greenhouse_record(self):
        record = normalize_record("Greenhouse", {
            "id": 7,
            "title": "Data Analyst",
            "location": {"name": "Remote"},
            "first_published": "2026-08-24T00:00:00Z",
            "absolute_url": "https://example.test/job/7",
        })
        self.assertEqual(record["location"], "Remote")
        self.assertEqual(record["application_url"], "https://example.test/job/7")

    def test_ashby_record(self):
        record = normalize_record("Ashby", {
            "id": "a1", "title": "Writer", "location": "Remote",
            "publishedAt": "2026-08-24", "applyUrl": "https://example.test/apply/a1",
        })
        self.assertEqual(record["title"], "Writer")

    def test_lever_record(self):
        record = normalize_record("Lever", {
            "id": "l1", "text": "Engineer", "categories": {"location": "Canada"},
            "createdAt": 1, "hostedUrl": "https://example.test/l1",
        })
        self.assertEqual(record["published_at"], 1)

    def test_smartrecruiters_documents_list_limitation(self):
        record = normalize_record("SmartRecruiters", {
            "id": "s1", "name": "Researcher", "location": {"fullLocation": "Montreal"},
            "releasedDate": "2026-08-24", "ref": "https://api.example.test/detail/s1",
        })
        self.assertIsNone(record["application_url"])

    def test_extract_and_metrics(self):
        records = extract_records("Ashby", {"jobs": [{"id": "1"}]})
        self.assertEqual(len(records), 1)
        normalized = [{"id": "1", "title": "A"}, {"id": "1", "title": None}]
        self.assertEqual(duplicate_count(normalized), 1)
        self.assertEqual(percentage(normalized, "title"), 50.0)


if __name__ == "__main__":
    unittest.main()
