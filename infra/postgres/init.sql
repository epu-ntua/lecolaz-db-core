CREATE TABLE IF NOT EXISTS file_metadata (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    object_key TEXT NOT NULL,
    content_type TEXT,
    size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT now(),
    extra JSONB
);
