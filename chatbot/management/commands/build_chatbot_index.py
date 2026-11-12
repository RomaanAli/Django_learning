import logging
from typing import List

from django.conf import settings
from django.core.management.base import BaseCommand

from chatbot.embeddings import EMBEDDING_MODEL_NAME, get_batch_embeddings
from chatbot.faqs import FAQS
from chatbot.models import KnowledgeChunk
from courses.models import Course, Lesson

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_words: int = 400, overlap_words: int = 60) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [text.strip()]

    chunks = []
    step = max_words - overlap_words
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + max_words]).strip()
        if chunk:
            chunks.append(chunk)
        if i + max_words >= len(words):
            break
    return chunks


class Command(BaseCommand):
    help = "Builds or updates the RAG knowledge index in PostgreSQL with pgvector."

    def handle(self, *args, **options):
        hf_token = getattr(settings, "HF_TOKEN", "").strip()
        if not hf_token:
            self.stderr.write(self.style.ERROR("HF_TOKEN is not configured in settings or .env file."))
            return

        self.stdout.write(self.style.NOTICE(f"Using Hugging Face Inference API ({EMBEDDING_MODEL_NAME})..."))

        raw_chunks = []

        faq_count = 0
        for faq in FAQS:
            title = faq["title"]
            content = faq["content"]
            url = faq.get("source_url", "")
            chunks = chunk_text(content)
            for chunk in chunks:
                raw_chunks.append({
                    "source_type": "faq",
                    "source_id": "",
                    "title": title,
                    "content": chunk,
                    "source_url": url,
                })
                faq_count += 1

        course_count = 0
        lesson_count = 0
        published_courses = Course.objects.filter(is_published=True).select_related("instructor")

        for course in published_courses:
            instructor_name = (
                course.instructor.get_full_name() or course.instructor.username
                if course.instructor else "Unknown"
            )
            course_text = (
                f"Course Title: {course.title}\n"
                f"Instructor: {instructor_name}\n"
                f"Price: ${course.price:.2f}\n"
                f"Description: {course.description or 'No description provided.'}"
            )
            chunks = chunk_text(course_text)
            for chunk in chunks:
                raw_chunks.append({
                    "source_type": "course",
                    "source_id": str(course.id),
                    "title": f"Course: {course.title}",
                    "content": chunk,
                    "source_url": f"/courses/{course.id}/",
                })
                course_count += 1

            lessons = course.lessons.all().order_by("order")
            for lesson in lessons:
                lesson_text = (
                    f"Course: {course.title}\n"
                    f"Lesson #{lesson.order}: {lesson.title}\n"
                    f"Content: {lesson.content or 'No content provided.'}"
                )
                l_chunks = chunk_text(lesson_text)
                for chunk in l_chunks:
                    raw_chunks.append({
                        "source_type": "lesson",
                        "source_id": str(lesson.id),
                        "title": f"Lesson: {lesson.title} ({course.title})",
                        "content": chunk,
                        "source_url": f"/courses/{course.id}/",
                    })
                    lesson_count += 1

        self.stdout.write(
            f"Collected {len(raw_chunks)} chunks: "
            f"{faq_count} FAQ, {course_count} Course, {lesson_count} Lesson."
        )

        if not raw_chunks:
            self.stdout.write(self.style.WARNING("No chunks to index."))
            return

        texts_to_embed = [
            f"{chunk['title']}\n{chunk['content']}" for chunk in raw_chunks
        ]
        self.stdout.write(f"Generating 384-d embeddings via Hugging Face Inference API for {len(texts_to_embed)} chunks...")
        embeddings = get_batch_embeddings(texts_to_embed, hf_token=hf_token, batch_size=10, pause_between_batches=0.5)

        KnowledgeChunk.objects.all().delete()

        chunks_to_create = []
        for meta, embedding in zip(raw_chunks, embeddings):
            chunks_to_create.append(
                KnowledgeChunk(
                    source_type=meta["source_type"],
                    source_id=meta["source_id"],
                    title=meta["title"],
                    content=meta["content"],
                    source_url=meta["source_url"],
                    embedding=embedding,
                )
            )

        KnowledgeChunk.objects.bulk_create(chunks_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully indexed {len(chunks_to_create)} knowledge chunks into PostgreSQL! "
                f"({faq_count} FAQ chunks, {course_count} Course chunks, {lesson_count} Lesson chunks)"
            )
        )

