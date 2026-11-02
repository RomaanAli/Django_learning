from django.conf import settings
from django.db import models
from pgvector.django import VectorField


class KnowledgeChunk(models.Model):
    SOURCE_TYPE_CHOICES = [
        ('course', 'Course'),
        ('lesson', 'Lesson'),
        ('faq', 'FAQ'),
    ]

    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    source_id = models.CharField(max_length=100, blank=True, default='')
    title = models.CharField(max_length=255)
    content = models.TextField()
    source_url = models.CharField(max_length=500, blank=True, default='')
    embedding = VectorField(dimensions=384)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['source_type']),
        ]

    def __str__(self):
        return f"[{self.source_type}] {self.title}"


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_messages',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} ({self.role}): {self.content[:30]}"
