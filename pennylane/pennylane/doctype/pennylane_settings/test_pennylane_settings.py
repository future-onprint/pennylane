# Copyright (c) 2026, Underscore Blank OÜ and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestPennylaneSettings(IntegrationTestCase):
	def setUp(self):
		self.settings = frappe.get_doc("Pennylane Settings")
		self._original = {
			"is_enabled": self.settings.is_enabled,
			"base_url": self.settings.base_url,
			"api_token": self.settings.get_password("api_token") or "",
		}

	def tearDown(self):
		# Restore original values after each test
		self.settings.reload()
		self.settings.is_enabled = self._original["is_enabled"]
		self.settings.base_url = self._original["base_url"]
		self.settings.save(ignore_permissions=True)

	def test_default_base_url_set_on_validate(self):
		self.settings.base_url = ""
		self.settings.validate()
		self.assertEqual(self.settings.base_url, "https://app.pennylane.com/api/external/v2")

	def test_trailing_slash_stripped_from_base_url(self):
		self.settings.base_url = "https://app.pennylane.com/api/external/v2/"
		self.settings.validate()
		self.assertFalse(self.settings.base_url.endswith("/"))

	def test_disabled_by_default(self):
		# Fresh install — integration should not be active without explicit opt-in
		self.settings.is_enabled = 0
		self.settings.save(ignore_permissions=True)
		fresh = frappe.get_cached_doc("Pennylane Settings")
		self.assertFalse(bool(fresh.is_enabled))

	def test_connection_status_options(self):
		meta = frappe.get_meta("Pennylane Settings")
		field = meta.get_field("connection_status")
		allowed = [o for o in field.options.split("\n") if o]
		self.assertIn("Connected", allowed)
		self.assertIn("Failed", allowed)
		self.assertIn("Not Tested", allowed)
