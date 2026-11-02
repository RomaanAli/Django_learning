from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from chatbot.admin import rebuild_knowledge_chunks
from chatbot.models import KnowledgeChunk
from courses.models import Course

User = get_user_model()


class RebuildIndexEndpointTests(TestCase):
    """
    Step 8 Test Suite: Verifies staff-only index rebuild endpoint and admin action.
    Ensures safe rebuilding on Render (without shell access) while blocking non-staff.
    """

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()
        self.rebuild_url = reverse("chatbot:rebuild_index")

        # Create regular student user
        self.student = User.objects.create_user(
            username="student_rebuild_test",
            email="student_rebuild@test.com",
            password="testpassword123",
            role=User.ROLE_STUDENT,
        )

        # Create staff user
        self.staff_user = User.objects.create_user(
            username="staff_rebuild_test",
            email="staff_rebuild@test.com",
            password="testpassword123",
            is_staff=True,
            role=User.ROLE_ADMIN,
        )

        # Create sample published course so indexing has content
        self.course = Course.objects.create(
            title="Django Rebuild Test Course",
            description="Testing the rebuild index endpoint.",
            price=0.00,
            is_published=True,
            instructor=self.staff_user,
        )

    def test_anonymous_user_blocked(self):
        """Unauthenticated requests must be blocked with 401 Unauthorized."""
        response = self.client.post(self.rebuild_url)
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertIn("error", data)

    def test_student_user_forbidden(self):
        """Regular student must receive 403 Forbidden."""
        self.client.force_login(self.student)
        response = self.client.post(self.rebuild_url)
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("Forbidden", data["error"])

    def test_staff_user_can_trigger_rebuild_success(self):
        """Staff user must be able to trigger rebuild and receive 200 OK with success message."""
        self.client.force_login(self.staff_user)
        response = self.client.post(self.rebuild_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("Successfully rebuilt", data.get("message", ""))
        self.assertGreater(data.get("total_chunks", 0), 0)

        # Verify chunks exist in database
        self.assertTrue(KnowledgeChunk.objects.filter(source_type="course").exists())

    def test_admin_action_triggers_rebuild(self):
        """The Django admin action rebuild_knowledge_chunks must run cleanly and report success."""
        request = self.factory.post("/admin/chatbot/knowledgechunk/")
        request.user = self.staff_user

        # Attach messages framework mock
        setattr(request, "session", "mock_session")
        messages = FallbackStorage(request)
        setattr(request, "_messages", messages)

        # Execute admin action
        rebuild_knowledge_chunks(None, request, KnowledgeChunk.objects.none())

        # Check success message was queued
        message_texts = [m.message for m in messages]
        self.assertTrue(any("Successfully rebuilt knowledge base index" in msg for msg in message_texts))
