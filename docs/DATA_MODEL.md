# Схема данных

## Сущности и связи

```
Author (1) ────< (N) Book (N) >──── (1) Faculty
                        │
                        │ (1)
                        │
                        ∨ (N)
                      Copy (N) >──── (1) Branch
                        │
                        │ (1)
                        │
                        ∨ (N)
                       Loan
```

- **Author** (автор) - 1 автор может иметь много книг.
- **Faculty** (факультет) - к какому направлению относится книга (необязательная связь).
- **Book** (книга) - справочная единица: название, автор, факультет, год издания, ISBN.
- **Branch** (филиал) - физическое место хранения.
- **Copy** (экземпляр) - конкретный физический экземпляр книги в конкретном филиале,
  имеет статус: `available`/`issued`/`lost`.
- **Loan** (выдача/использование) - история выдач конкретного экземпляра:
  кто взял, когда выдан, когда возвращен (`returned_at IS NULL` = выдача еще активна).

## Бизнес-правило

Экземпляр (`Copy`) нельзя выдать (`POST /loans`), если у него уже есть активная
выдача (`status = issued`). Сначала нужно оформить возврат (`POST /loans/{id}/return`).
Реализация: `app/crud.py::issue_copy`. Проверка: `tests/test_loans.py`.

## Таблица полей

| Таблица   | Ключевые поля                                                  |
|-----------|------------------------------------------------------------------|
| authors   | id, full_name, bio                                                |
| faculties | id, name (unique)                                                 |
| branches  | id, name (unique), address                                       |
| books     | id, title, isbn (unique), published_year, author_id, faculty_id  |
| copies    | id, inventory_number (unique), status, book_id, branch_id        |
| loans     | id, copy_id, borrower_name, issued_at, returned_at (nullable)     |
