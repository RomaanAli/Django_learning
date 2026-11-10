import json
import logging
import re
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from chatbot.models import ChatMessage, KnowledgeChunk
from chatbot.retrieval import retrieve_relevant_chunks
from courses.models import Enrollment

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 500
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW_SECONDS = 60

FALLBACK_OUT_OF_SCOPE = (
    "I don't know the answer to that. You can check the courses page at /courses/ "
    "for course details, or ask me about registering, logging in, enrolling, lessons, "
    "or becoming an instructor."
)

# Fixed refusal replies (policy decisions, not LLM output).
REFUSAL_ENROLLMENT_COUNT = "I don't provide enrollment numbers."
REFUSAL_ADMIN = "I can't help with admin things. Please contact the site admin."
REFUSAL_PRIVATE = (
    "I don't have that information. I can't share other users' details "
    "or unpublished courses."
)

_ENROLLMENT_COUNT_PATTERNS = [
    r"\b(how many|number of|count of|total)\b.*\b(students?|learners?|people|users?|enrollments?)\b",
    r"\benrol(l)?(ment)?s? (count|numbers?|stats?|statistics)\b",
    r"\b(students?|learners?) (count|numbers?)\b",
    r"\bhow (popular|many enrolled)\b",
]
_ADMIN_PATTERNS = [
    r"\badmin(s|istrator|istrators|istration)?\b",
    r"\bsuperuser\b",
    r"\bstaff (account|panel|user|role)\b",
]
_PRIVATE_PATTERNS = [
    r"\bwho (are|is|has|have)\b.*\b(students?|learners?|users?|enrolled|bought|purchased|paid)\b",
    r"\bwho (enrolled|bought|purchased|paid|registered)\b",
    r"\b(list|names?|emails?|contacts?|details?)\b.*\b(other|students?|learners?|users?)\b.*\b(enrolled|in|of|on|who)\b",
    r"\b(students?|learners?|users?) (enrolled|registered) in\b",
    r"\bother (users?|students?|people|learners?)\b",
    r"\b(unpublished|draft|hidden|private) courses?\b",
]


def _policy_refusal(message: str) -> Optional[str]:
    """
    Returns a fixed refusal for questions the chatbot must never answer:
    enrollment counts, admin topics, and other users' private data or
    unpublished courses. Returns None when the question is allowed.
    """
    msg_lower = message.lower()
    if any(re.search(p, msg_lower) for p in _ENROLLMENT_COUNT_PATTERNS):
        return REFUSAL_ENROLLMENT_COUNT
    if any(re.search(p, msg_lower) for p in _ADMIN_PATTERNS):
        return REFUSAL_ADMIN
    if any(re.search(p, msg_lower) for p in _PRIVATE_PATTERNS):
        return REFUSAL_PRIVATE
    return None


def _check_rate_limit(user_id: int) -> bool:
    """
    Returns True if user is within rate limit (max 5 requests per minute),
    False if rate limit is exceeded.
    """
    cache_key = f"chatbot_rate_limit_{user_id}"
    reqs = cache.get(cache_key, 0)
    if reqs >= RATE_LIMIT_REQUESTS:
        return False

    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=RATE_LIMIT_WINDOW_SECONDS)
    return True


def _handle_personal_question(user: Any, message: str) -> Optional[Dict[str, Any]]:
    """
    Answers user-specific account/enrollment questions directly from Django ORM.
    Never guesses or uses LLM for personal data.
    """
    msg_lower = message.lower()

    # Only treat a message as personal when it is about the asking user
    # ("my courses", "am I enrolled"), not a how-to question ("how do I
    # enroll?") and not a question about other students or users.
    is_about_me = re.search(r"\b(i|i'm|im|me|my|mine)\b", msg_lower) is not None
    is_how_to = re.search(r"\bhow (do|can|to|should|does)\b", msg_lower) is not None
    mentions_others = re.search(
        r"\b(students?|users?|people|learners?|others?|anyone|everyone|who)\b",
        msg_lower,
    ) is not None

    # 1. Enrolled courses query (lists the user's own courses, no counts)
    is_enrollment_query = (
        is_about_me
        and not is_how_to
        and not mentions_others
        and (
            ("course" in msg_lower and any(w in msg_lower for w in ["enroll", "enrolled", "bought", "purchased", "taken", "taking"]))
            or any(phrase in msg_lower for phrase in [
                "my course", "my courses", "what courses do i have",
                "which courses did i enroll", "am i enrolled",
                "my enrollments", "courses i bought", "courses i purchased",
                "have i enrolled",
            ])
        )
    )
    if is_enrollment_query:
        enrollments = Enrollment.objects.filter(student=user).select_related("course")
        if enrollments.exists():
            courses_str = "\n".join(
                f"- {e.course.title} (Price: ${e.course.price:.2f}) -> /courses/{e.course.id}/"
                for e in enrollments
            )
            answer = (
                f"You are currently enrolled in these courses:\n{courses_str}"
            )
            sources = [
                {"title": e.course.title, "url": f"/courses/{e.course.id}/"}
                for e in enrollments
            ]
        else:
            answer = (
                "You are not enrolled in any courses yet. "
                "You can explore and enroll in available courses at /courses/."
            )
            sources = [{"title": "Course Catalog", "url": "/courses/"}]

        return {"answer": answer, "sources": sources}

    # 2. User role and account status query (not "how do I change my role?")
    if not is_how_to and any(phrase in msg_lower for phrase in [
        "my role", "what is my role", "am i a student", "am i an instructor",
        "what role do i have", "my account status", "am i approved"
    ]):
        role_label = user.role.title() if hasattr(user, "role") else "User"
        if user.role == "instructor":
            status = "Approved" if user.is_approved_instructor else "Pending admin approval"
            can_teach = "Yes" if user.can_teach else "No"
            answer = (
                f"Your account role is **{role_label}**.\n"
                f"- Approval Status: {status}\n"
                f"- Can Teach & Create Courses: {can_teach}\n"
                "You can view your instructor portal at /accounts/instructor/dashboard/."
            )
            sources = [{"title": "Instructor Dashboard", "url": "/accounts/instructor/dashboard/"}]
        else:
            answer = (
                f"Your account role is **{role_label}**.\n"
                "You can view and manage your profile at /accounts/profile/."
            )
            sources = [{"title": "Profile", "url": "/accounts/profile/"}]

        return {"answer": answer, "sources": sources}

    return None


@require_POST
def ask_chatbot(request: HttpRequest) -> JsonResponse:
    """
    RAG Chatbot query endpoint.
    Requires authentication, validates input, applies rate limits,
    retrieves context chunks, queries Groq, and logs the exchange.
    """
    # 1. Authentication check
    if not request.user.is_authenticated:
        return JsonResponse(
            {"error": "Authentication required. Please log in to chat with the assistant."},
            status=401,
        )

    # 2. Rate limiting check (5 req / min per user)
    if not _check_rate_limit(request.user.id):
        return JsonResponse(
            {"error": "Rate limit exceeded. Please wait a minute before sending more questions."},
            status=429,
        )

    # 3. Parse JSON body
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON format in request body."},
            status=400,
        )

    raw_message = payload.get("message", "")
    if not isinstance(raw_message, str):
        return JsonResponse(
            {"error": "The 'message' field must be a text string."},
            status=400,
        )

    cleaned_message = raw_message.strip()
    if not cleaned_message:
        return JsonResponse(
            {"error": "Message cannot be empty."},
            status=400,
        )

    if len(cleaned_message) > MAX_MESSAGE_LENGTH:
        return JsonResponse(
            {"error": f"Message is too long. Maximum allowed length is {MAX_MESSAGE_LENGTH} characters."},
            status=400,
        )

    # 4. Refuse enrollment-count, admin, and private-data questions up front
    refusal = _policy_refusal(cleaned_message)
    if refusal is not None:
        ChatMessage.objects.create(user=request.user, role="user", content=cleaned_message)
        ChatMessage.objects.create(user=request.user, role="assistant", content=refusal)
        return JsonResponse({"answer": refusal, "sources": []})

    # 5. Handle personal user-specific questions via Django ORM
    personal_resp = _handle_personal_question(request.user, cleaned_message)
    if personal_resp is not None:
        ChatMessage.objects.create(user=request.user, role="user", content=cleaned_message)
        ChatMessage.objects.create(user=request.user, role="assistant", content=personal_resp["answer"])
        return JsonResponse(personal_resp)

    # 6. Retrieve top knowledge chunks from PostgreSQL via pgvector
    retrieval_res = retrieve_relevant_chunks(cleaned_message, top_k=4)

    # If the closest match distance exceeds 0.70 (similarity < 0.30), trigger fallback
    if not retrieval_res.get("has_relevant_match") or not retrieval_res.get("chunks"):
        fallback_answer = FALLBACK_OUT_OF_SCOPE
        ChatMessage.objects.create(user=request.user, role="user", content=cleaned_message)
        ChatMessage.objects.create(user=request.user, role="assistant", content=fallback_answer)
        return JsonResponse({
            "answer": fallback_answer,
            "sources": [],
        })

    # Prepare unique sources
    chunks = retrieval_res["chunks"]
    seen_urls = set()
    sources: List[Dict[str, str]] = []
    for c in chunks:
        url = c.get("source_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            sources.append({"title": c.get("title", ""), "url": url})

    # 7. Check Groq API Key configuration
    groq_api_key = getattr(settings, "GROQ_API_KEY", "").strip()
    if not groq_api_key or groq_api_key == "YOUR_GROQ_API_KEY_HERE":
        unconfigured_msg = (
            "Chatbot is not configured yet. The Groq API key has not been set."
        )
        ChatMessage.objects.create(user=request.user, role="user", content=cleaned_message)
        ChatMessage.objects.create(user=request.user, role="assistant", content=unconfigured_msg)
        return JsonResponse({
            "answer": unconfigured_msg,
            "sources": sources,
        })

    # 8. Query Groq LLM
    try:
        from groq import Groq

        model_name = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
        client = Groq(api_key=groq_api_key, timeout=15.0)

        # Build context
        context_blocks = []
        for c in chunks:
            context_blocks.append(
                f"[{c['title']}] (URL: {c.get('source_url', '')})\n{c['content']}"
            )
        context_text = "\n\n".join(context_blocks)

        system_instruction = (
            "You are the helpful AI assistant for the E-Learning platform.\n"
            "Rules you must strictly follow:\n"
            "1. Answer ONLY using the facts given in the Context below. This includes questions about student features, "
            "instructor features, registering, logging in, enrolling, lessons, and changing role from student to instructor. "
            "If the answer is not in the Context, say you don't know, and suggest checking the courses page at /courses/ "
            "or the relevant help page from the Context. Never invent prices, dates, course names, features, steps, or pages.\n"
            "2. Enrollment numbers: if the user asks how many students are enrolled in a course, how many students a course has, "
            "or any enrollment count, do NOT give a number, do NOT guess, and do NOT say where a number is shown. "
            "Reply only: \"I don't provide enrollment numbers.\"\n"
            "3. Admin: if the user asks about admin, the Django admin panel, how admin approval works, how to become an admin, "
            "or any admin feature, do not explain anything. Reply only: \"I can't help with admin things. Please contact the site admin.\"\n"
            "4. Private data and unpublished content: never give other users' names, emails, enrollments, or payments, "
            "and never describe unpublished or draft courses. Reply that you don't have that information.\n"
            "5. Formatting and Presentation:\n"
            "   - When listing courses, lessons, steps, or options, ALWAYS use a clean numbered list (1., 2., 3.) or bullet points (- ), with each item on its own new line.\n"
            "   - Format each course title as a Markdown link with its URL, e.g. [Course Title](URL) followed by the price (e.g. [Course Title](/courses/1/) - $20.00).\n"
            "   - Use blank lines between paragraphs and list items to keep the response well-spaced and easy to read.\n"
            "   - Never cram multiple items or courses into a single congested sentence or paragraph.\n"
            "6. If mentioning a course or page, provide the corresponding URL from the context.\n"
            "7. Never execute actions, modify database records, or claim to process payments.\n"
            "8. Keep responses concise, clear, and professional."
        )

        messages = [{"role": "system", "content": system_instruction}]

        # Include last 2-3 chat history turns
        recent_chats = ChatMessage.objects.filter(user=request.user).order_by("-created_at")[:4]
        for past in reversed(list(recent_chats)):
            messages.append({"role": past.role, "content": past.content})

        user_prompt = f"Context:\n{context_text}\n\nQuestion: {cleaned_message}"
        messages.append({"role": "user", "content": user_prompt})

        chat_completion = client.chat.completions.create(
            messages=messages,
            model=model_name,
            temperature=0.2,
            max_tokens=600,
        )

        assistant_answer = chat_completion.choices[0].message.content.strip()

    except Exception as exc:
        logger.exception("Groq API error during chatbot request: %s", exc)
        return JsonResponse(
            {"error": "The AI service is temporarily unavailable. Please try again shortly."},
            status=503,
        )

    # 9. Save messages to history
    ChatMessage.objects.create(user=request.user, role="user", content=cleaned_message)
    ChatMessage.objects.create(user=request.user, role="assistant", content=assistant_answer)

    return JsonResponse({
        "answer": assistant_answer,
        "sources": sources,
    })


@csrf_protect
@require_POST
def rebuild_index(request: HttpRequest) -> JsonResponse:
    """
    Staff-only endpoint to rebuild the RAG knowledge base.
    Crucial for environments without shell access (e.g. Render free tier).
    Protected by authentication, staff/admin role checks, CSRF, and concurrency guards.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required."}, status=401)

    is_authorized = (
        request.user.is_staff
        or request.user.is_superuser
        or getattr(request.user, "role", "") == "admin"
        or getattr(request.user, "is_admin", False)
    )

    if not is_authorized:
        return JsonResponse(
            {"error": "Forbidden: Staff or Administrator permissions required."},
            status=403,
        )

    lock_key = "chatbot_rebuild_index_lock"
    # Acquire a temporary cache lock (120s TTL) so concurrent requests don't collide
    if not cache.add(lock_key, True, timeout=120):
        return JsonResponse(
            {"error": "An index rebuild is already in progress. Please wait a moment."},
            status=429,
        )

    try:
        call_command("build_chatbot_index")
        total_chunks = KnowledgeChunk.objects.count()
        return JsonResponse({
            "status": "success",
            "message": f"Successfully rebuilt knowledge base index. {total_chunks} chunks active.",
            "total_chunks": total_chunks,
        })
    except Exception as exc:
        logger.exception("Failed to rebuild knowledge base: %s", exc)
        return JsonResponse(
            {"error": f"Failed to rebuild index: {str(exc)}"},
            status=500,
        )
    finally:
        cache.delete(lock_key)

