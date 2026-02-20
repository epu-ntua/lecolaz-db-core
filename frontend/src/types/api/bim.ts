export type BimFileDto = {
  id: string;
  file_id: string;
  filename: string;
  format: string;
  schema: string | null;
  created_at: string | null;
  extra: Record<string, unknown> | null;
};

export type BimMetadataDto = {
  id: string;
  filename: string;
  upload_date: string | null;
  size: number | null;
  content_type: string | null;
};
