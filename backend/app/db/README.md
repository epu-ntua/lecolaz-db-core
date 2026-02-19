# Database Schema Workflow (ORM)

## Where Schemas Live

- All tables are defined in ORM models
- Location:

```
app/db/models/
```

Each table = one Python class.

Example:

```py
class FileMetadata(Base):
    __tablename__ = "file_metadata"
```

## Creating A New Table

1. Create a new model file under `app/db/models/`
2. Define the ORM class (columns, constraints)
3. Do not touch Postgres directly
4. Import the new model in the registry at app/db/models/__init__.py

## Editing An Existing Table

1. Edit the corresponding ORM model:
2. Add/remove columns
3. Change nullability
4. Add indexes / constraints
5. Save the file
6. Do not apply changes manually in the DB
7. See alembic/README.md for instructions on applying changes

## Important Rules

- ORM models are the single source of truth
- No `CREATE TABLE` / `ALTER TABLE` in pgAdmin
- No schema logic in `init.sql`
