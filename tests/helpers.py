"""Вспомогательные функции для подготовки данных через HTTP API."""


def create_author(client, name="Author X"):
    return client.post("/authors", json={"full_name": name}).json()


def create_book(client, author_id, title="Book X", **extra):
    return client.post("/books", json={"title": title, "author_id": author_id, **extra}).json()


def create_branch(client, name="Central", address=None):
    return client.post("/branches", json={"name": name, "address": address}).json()


def create_copy(client, book_id, branch_id, inventory_number="INV-001"):
    payload = {"inventory_number": inventory_number, "book_id": book_id, "branch_id": branch_id}
    return client.post("/copies", json=payload).json()


def issue(client, copy_id, borrower="Ivan", **extra):
    return client.post("/loans", json={"copy_id": copy_id, "borrower_name": borrower, **extra})


def make_copy(client, inventory_number="INV-001"):
    """Автор + книга + филиал + один экземпляр; возвращает словарь экземпляра."""
    author = create_author(client)
    book = create_book(client, author["id"])
    branch = create_branch(client)
    return create_copy(client, book["id"], branch["id"], inventory_number)
