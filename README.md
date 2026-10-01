# Document Search Service

Простой асинхронный сервис поиска по текстам документов. Полные документы
хранятся в PostgreSQL, а Elasticsearch используется как поисковый индекс.

## Стек

- Python 3.12+
- FastAPI
- SQLAlchemy и asyncpg
- PostgreSQL 15
- Elasticsearch 9
- Alembic
- Docker Compose
- uv

## Запуск в Docker

Соберите образы и запустите все сервисы:

```bash
docker compose up -d --build
```

Примените миграции:

```bash
docker exec search_documents_api uv run alembic upgrade head
```

Импортируйте `data/posts.csv` в PostgreSQL и Elasticsearch:

```bash
docker exec search_documents_api uv run import-data
```

Сервис будет доступен по адресу `http://localhost:8070`.
Импорт нужно выполнить один раз после создания пустой базы данных.

После импорта проверить наличие всех 1500 документов в Elasticsearch можно по
адресу:

[http://localhost:9200/documents/_search?pretty&amp;size=1500](http://localhost:9200/documents/_search?pretty&size=1500)

Чтобы остановить контейнеры и удалить сохранённые данные:

```bash
docker compose down -v
```

## API

### Поиск документов

```http
GET /search-documents?input_text=новый%20скин&limit=20&mode=any
```

Параметры:

- `input_text` — обязательный поисковый запрос;
- `limit` — количество документов от 1 до 20, по умолчанию 20;
- `mode` — режим поиска, по умолчанию `any`.

Режимы поиска:

- `any` — документ содержит хотя бы одно слово из запроса;
- `all` — документ содержит все слова из запроса;
- `phrase` — слова встречаются рядом и в указанном порядке;
- `fuzzy` — допускаются небольшие опечатки в словах.

Пример с curl:

```bash
curl --get "http://localhost:8070/search-documents" \
  --data-urlencode "input_text=новый скин" \
  --data-urlencode "limit=20" \
  --data-urlencode "mode=any"
```

Найденные идентификаторы получает Elasticsearch. Полные документы загружаются
из PostgreSQL и возвращаются с сортировкой по `created_date` по убыванию.

### Удаление документа

```http
DELETE /delete-document?document_id=1
```

Пример с curl:

```bash
curl -X DELETE "http://localhost:8070/delete-document?document_id=1"
```

Успешное удаление возвращает `204 No Content`. Если документ не найден,
возвращается `404 Not Found`.

## Тесты

Тесты не требуют запущенных PostgreSQL и Elasticsearch:

```bash
uv run pytest
```

## Документация

- Swagger UI: `http://localhost:8070/docs`
- OpenAPI во время работы сервиса: `http://localhost:8070/openapi.json`
- Сохранённая OpenAPI-схема: [`docs.json`](docs.json)
