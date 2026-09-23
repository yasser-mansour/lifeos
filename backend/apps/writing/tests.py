from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Profile
from apps.writing.models import Book, Chapter


class ChapterModelTests(TestCase):
    def test_word_count_computed_on_save(self):
        book = Book.objects.create(title="My Book")
        chapter = Chapter.objects.create(book=book, title="One", content="one two three four")
        self.assertEqual(chapter.word_count, 4)

    def test_book_total_word_count_sums_chapters(self):
        book = Book.objects.create(title="My Book")
        Chapter.objects.create(book=book, content="one two three")
        Chapter.objects.create(book=book, content="four five")
        self.assertEqual(book.total_word_count, 5)


class WritingViewTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="owner", password="testpass123")
        Profile.objects.create(user=user, display_name="Owner")
        self.client.login(username="owner", password="testpass123")

    def test_empty_state(self):
        response = self.client.get(reverse("writing:library"))
        self.assertContains(response, "Nothing here yet")

    def test_create_book_and_chapter(self):
        response = self.client.post(reverse("writing:book_create"), {"title": "Novel", "status": "drafting"})
        book = Book.objects.get(title="Novel")
        self.assertRedirects(response, book.get_absolute_url())
        self.client.get(reverse("writing:chapter_create", args=[book.pk]))
        self.assertEqual(book.chapters.count(), 1)

    def test_chapter_autosave_updates_word_count(self):
        book = Book.objects.create(title="Novel")
        chapter = Chapter.objects.create(book=book)
        response = self.client.post(reverse("writing:chapter_autosave", args=[chapter.pk]), {
            "title": "Chapter One", "content": "It was a dark and stormy night.", "status": "draft",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["word_count"], 7)
