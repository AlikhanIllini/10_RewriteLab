"""
Tests for the LLM rewrite generation feature.

Covers:
- Prompt builder produces correct message structure
- POST endpoint creates RewriteResult rows (LLM call mocked)
- Missing API key returns friendly error without crashing
- Regenerate replaces old results
"""

import json
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse

from rewrites.models import (
    RewriteContext,
    ToneOption,
    RewriteSession,
    RewriteResult,
)
from rewrites.services.llm_rewrite import (
    build_prompt,
    compute_quality_score,
    generate_rewrites_for_session,
)


class _SessionMixin:
    """Helper to create test fixtures."""

    def _create_session(self, **overrides):
        ctx, _ = RewriteContext.objects.get_or_create(
            name="Professional Email",
            defaults={
                "description": "Emails in a workplace setting",
                "guidelines": "Be concise and respectful.",
            },
        )
        tone, _ = ToneOption.objects.get_or_create(
            name="Clear",
            defaults={
                "description": "Direct and unambiguous",
                "prompt_modifier": "Write clearly and directly.",
            },
        )
        defaults = dict(
            original_text="Hi professor, I was wondering if maybe I could possibly get an extension on the assignment that is due tomorrow because I have been really busy.",
            context=ctx,
            tone=tone,
            audience="professor",
            purpose="request deadline extension",
            session_token="test-token-1234",
        )
        defaults.update(overrides)
        return RewriteSession.objects.create(**defaults)


# ── Prompt builder tests ────────────────────────────────────────────────────

class BuildPromptTest(_SessionMixin, TestCase):
    def test_prompt_structure(self):
        session = self._create_session()
        messages = build_prompt(session)

        # Should have 3 messages: system, developer, user
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "developer")
        self.assertEqual(messages[2]["role"], "user")

    def test_system_message_content(self):
        session = self._create_session()
        messages = build_prompt(session)
        self.assertIn("professional editor", messages[0]["content"])

    def test_developer_message_includes_context(self):
        session = self._create_session()
        messages = build_prompt(session)
        dev = messages[1]["content"]
        self.assertIn("Professional Email", dev)
        self.assertIn("Be concise and respectful.", dev)

    def test_developer_message_includes_tone(self):
        session = self._create_session()
        messages = build_prompt(session)
        dev = messages[1]["content"]
        self.assertIn("Clear", dev)
        self.assertIn("Write clearly and directly.", dev)

    def test_developer_message_includes_audience_purpose(self):
        session = self._create_session()
        messages = build_prompt(session)
        dev = messages[1]["content"]
        self.assertIn("professor", dev)
        self.assertIn("request deadline extension", dev)

    def test_user_message_is_original_text(self):
        session = self._create_session()
        messages = build_prompt(session)
        self.assertEqual(messages[2]["content"], session.original_text)

    def test_prompt_without_audience_purpose(self):
        session = self._create_session(audience="", purpose="")
        messages = build_prompt(session)
        dev = messages[1]["content"]
        self.assertNotIn("Audience:", dev)
        self.assertNotIn("Purpose:", dev)


# ── Quality heuristic tests ─────────────────────────────────────────────────

class QualityScoreTest(TestCase):
    def test_shorter_no_filler_is_high(self):
        original = "This is a somewhat long and rambling sentence that goes on."
        rewritten = "This sentence is concise."
        self.assertEqual(compute_quality_score(original, rewritten), "high")

    def test_filler_phrase_is_medium(self):
        original = "Please review the report."
        rewritten = "I hope this email finds you well. Please review the report."
        self.assertEqual(compute_quality_score(original, rewritten), "medium")

    def test_empty_rewrite_is_low(self):
        self.assertEqual(compute_quality_score("Some text", ""), "low")
        self.assertEqual(compute_quality_score("Some text", "   "), "low")


# ── Service integration (mocked LLM) ────────────────────────────────────────

MOCK_LLM_RESPONSE = {
    "rewrites": [
        {
            "version_label": "A",
            "rewritten_text": "Could I get an extension on tomorrow's assignment? I've been swamped.",
            "change_summary": "Made the request direct and concise.",
        },
        {
            "version_label": "B",
            "rewritten_text": "I'd like to request an extension on the assignment due tomorrow, as my schedule has been unusually full.",
            "change_summary": "Balanced clarity with politeness.",
        },
        {
            "version_label": "C",
            "rewritten_text": "Would it be possible to extend the deadline for tomorrow's assignment? I've had an especially busy stretch.",
            "change_summary": "Added warmth while staying concise.",
        },
    ]
}


def _mock_openai_create(**kwargs):
    """Fake OpenAI chat.completions.create response."""
    choice = MagicMock()
    choice.message.content = json.dumps(MOCK_LLM_RESPONSE)
    response = MagicMock()
    response.choices = [choice]
    return response


class GenerateRewritesServiceTest(_SessionMixin, TestCase):
    @patch("rewrites.services.llm_rewrite._get_client")
    def test_creates_three_results(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client

        session = self._create_session()
        results = generate_rewrites_for_session(session)

        self.assertEqual(len(results), 3)
        self.assertTrue(all(isinstance(r, RewriteResult) for r in results))

    @patch("rewrites.services.llm_rewrite._get_client")
    def test_session_marked_completed(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client

        session = self._create_session()
        self.assertFalse(session.is_completed)

        generate_rewrites_for_session(session)
        session.refresh_from_db()
        self.assertTrue(session.is_completed)

    @patch("rewrites.services.llm_rewrite._get_client")
    def test_version_labels(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client

        session = self._create_session()
        results = generate_rewrites_for_session(session)

        labels = sorted(r.version_label for r in results)
        self.assertEqual(labels, ["A", "B", "C"])

    @patch("rewrites.services.llm_rewrite._get_client")
    def test_word_counts_populated(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client

        session = self._create_session()
        results = generate_rewrites_for_session(session)

        for r in results:
            self.assertGreater(r.word_count_original, 0)
            self.assertGreater(r.word_count_rewritten, 0)

    @patch("rewrites.services.llm_rewrite._get_client")
    def test_regenerate_replaces_old_results(self, mock_get_client):
        client = MagicMock()
        client.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client

        session = self._create_session()

        # Generate first time
        generate_rewrites_for_session(session)
        self.assertEqual(session.results.count(), 3)
        old_ids = set(session.results.values_list("id", flat=True))

        # Regenerate
        generate_rewrites_for_session(session)
        self.assertEqual(session.results.count(), 3)
        new_ids = set(session.results.values_list("id", flat=True))

        # Old rows should be gone
        self.assertTrue(old_ids.isdisjoint(new_ids))


# ── View / endpoint tests ───────────────────────────────────────────────────

class GenerateRewritesViewTest(_SessionMixin, TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_not_allowed(self):
        session = self._create_session()
        url = reverse("rewrites:generate_rewrites", kwargs={"pk": session.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 405)  # Method Not Allowed

    @patch("rewrites.services.llm_rewrite._get_client")
    def test_post_full_integration_with_mock(self, mock_get_client):
        """Full integration: POST → service → mock LLM → DB rows."""
        client_mock = MagicMock()
        client_mock.chat.completions.create.side_effect = _mock_openai_create
        mock_get_client.return_value = client_mock

        session = self._create_session()
        url = reverse("rewrites:generate_rewrites", kwargs={"pk": session.pk})
        resp = self.client.post(url)

        self.assertEqual(resp.status_code, 302)
        self.assertEqual(session.results.count(), 3)
        session.refresh_from_db()
        self.assertTrue(session.is_completed)

    @patch(
        "rewrites.services.llm_rewrite.os.getenv",
        return_value="",
    )
    def test_missing_api_key_shows_error(self, mock_env):
        """If no API key, user sees a friendly error, app doesn't crash."""
        session = self._create_session()
        url = reverse("rewrites:generate_rewrites", kwargs={"pk": session.pk})
        resp = self.client.post(url, follow=True)

        self.assertEqual(resp.status_code, 200)
        # Check for error message in the response
        self.assertContains(resp, "OPENAI_API_KEY")


# ── Authentication tests ─────────────────────────────────────────────────────

class AuthTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_creates_user_and_redirects(self):
        url = reverse("rewrites:register")
        resp = self.client.post(url, {
            "username": "newuser",
            "email": "new@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        })
        self.assertEqual(resp.status_code, 302)
        from django.contrib.auth.models import User
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_auto_logs_in(self):
        url = reverse("rewrites:register")
        self.client.post(url, {
            "username": "newuser2",
            "email": "new2@example.com",
            "password1": "TestPass123!",
            "password2": "TestPass123!",
        })
        resp = self.client.get(reverse("rewrites:dashboard"))
        self.assertEqual(resp.status_code, 200)

    def test_login_works(self):
        from django.contrib.auth.models import User
        User.objects.create_user("testlogin", "t@t.com", "pass1234")
        resp = self.client.post(reverse("rewrites:login"), {
            "username": "testlogin",
            "password": "pass1234",
        })
        self.assertEqual(resp.status_code, 302)

    def test_login_bad_password(self):
        from django.contrib.auth.models import User
        User.objects.create_user("testlogin2", "t@t.com", "pass1234")
        resp = self.client.post(reverse("rewrites:login"), {
            "username": "testlogin2",
            "password": "wrongpass",
        })
        self.assertEqual(resp.status_code, 200)  # stays on login page

    def test_logout_redirects(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user("logoutuser", "t@t.com", "pass1234")
        self.client.login(username="logoutuser", password="pass1234")
        resp = self.client.get(reverse("rewrites:logout"))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("rewrites:dashboard"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)


# ── Session CRUD tests ──────────────────────────────────────────────────────

class SessionCRUDTest(_SessionMixin, TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("cruduser", "c@c.com", "pass1234")
        self.other_user = User.objects.create_user("other", "o@o.com", "pass1234")
        self.client.login(username="cruduser", password="pass1234")

    def _get_ctx_tone(self):
        ctx = RewriteContext.objects.create(
            name="Test Context",
            description="Test",
            guidelines="Be clear.",
        )
        tone = ToneOption.objects.create(
            name="Test Tone",
            description="Test",
            prompt_modifier="Be polite.",
        )
        return ctx, tone

    def test_create_session_get(self):
        resp = self.client.get(reverse("rewrites:session_create"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "New Rewrite Session")

    def test_create_session_post(self):
        ctx, tone = self._get_ctx_tone()
        resp = self.client.post(reverse("rewrites:session_create"), {
            "original_text": "This is a test email that needs to be rewritten to be more professional.",
            "context": ctx.pk,
            "tone": tone.pk,
            "audience": "boss",
            "purpose": "request feedback",
        })
        self.assertEqual(resp.status_code, 302)
        session = RewriteSession.objects.get(user=self.user)
        self.assertEqual(session.audience, "boss")
        self.assertEqual(session.user, self.user)

    def test_create_session_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("rewrites:session_create"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("login", resp.url)

    def test_edit_session(self):
        session = self._create_session()
        session.user = self.user
        session.save()
        resp = self.client.post(reverse("rewrites:session_edit", kwargs={"pk": session.pk}), {
            "original_text": "Updated text that is long enough to pass validation.",
            "context": session.context.pk,
            "tone": session.tone.pk,
            "audience": "updated audience",
            "purpose": "",
        })
        self.assertEqual(resp.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.audience, "updated audience")

    def test_edit_session_other_user_blocked(self):
        session = self._create_session()
        session.user = self.other_user
        session.save()
        resp = self.client.post(reverse("rewrites:session_edit", kwargs={"pk": session.pk}), {
            "original_text": "Hacked text!!! This should not work at all.",
            "context": session.context.pk,
            "tone": session.tone.pk,
        })
        self.assertEqual(resp.status_code, 302)
        session.refresh_from_db()
        self.assertNotIn("Hacked", session.original_text)

    def test_delete_session(self):
        session = self._create_session()
        session.user = self.user
        session.save()
        pk = session.pk
        resp = self.client.post(reverse("rewrites:session_delete", kwargs={"pk": pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(RewriteSession.objects.filter(pk=pk).exists())

    def test_delete_session_other_user_blocked(self):
        session = self._create_session()
        session.user = self.other_user
        session.save()
        pk = session.pk
        resp = self.client.post(reverse("rewrites:session_delete", kwargs={"pk": pk}))
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(RewriteSession.objects.filter(pk=pk).exists())


# ── Dashboard tests ──────────────────────────────────────────────────────────

class DashboardTest(_SessionMixin, TestCase):
    def setUp(self):
        self.client = Client()
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("dashuser", "d@d.com", "pass1234")
        self.client.login(username="dashuser", password="pass1234")

    def test_dashboard_shows_only_user_sessions(self):
        from django.contrib.auth.models import User
        other = User.objects.create_user("other2", "o@o.com", "pass1234")

        session_mine = self._create_session(session_token="mine-1234")
        session_mine.user = self.user
        session_mine.save()

        session_other = self._create_session(
            session_token="other-5678",
            original_text="A completely different text for the other user's session to avoid constraint.",
        )
        session_other.user = other
        session_other.save()

        resp = self.client.get(reverse("rewrites:dashboard"))
        self.assertContains(resp, session_mine.original_text[:20])
        self.assertNotContains(resp, "completely different text")


