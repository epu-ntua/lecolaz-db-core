export type FileDto = {
  id: string;
  filename: string;
  object_key: string;
  content_type: string | null;
  size_bytes: number | null;
  created_at: string;
  extra: Record<string, unknown> | null;
};
