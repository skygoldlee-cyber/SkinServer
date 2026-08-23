# deploy/db — 스키마 마이그레이션

- dev: gateway 가 `AUTO_DDL=1` 로 起動 시 스키마 보장(빠른 반복).
- 운영: auto-DDL 끄고 이 폴더의 순번 SQL 을 적용한다.
  ```bash
  for f in deploy/db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
  ```
- 스키마 변경은 새 순번 파일(0002_*.sql ...)로 추가(expand-contract).
  롤백 원칙: docs/architecture/03_DB_MIGRATION_ROLLBACK.md
