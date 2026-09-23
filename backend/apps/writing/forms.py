from apps.core.base_forms import StyledModelForm
from apps.writing.models import Book, Chapter


class BookForm(StyledModelForm):
    class Meta:
        model = Book
        fields = ["title", "description", "status"]


class ChapterForm(StyledModelForm):
    class Meta:
        model = Chapter
        fields = ["title", "content", "status"]
