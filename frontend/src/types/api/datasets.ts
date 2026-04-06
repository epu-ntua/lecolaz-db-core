export type DatasetUploadResult = {
  dataset_id: string;
  type: string;
  status: string;
};

export type DatasetDto = {
  id: string;
  type: string;
  subtype: string | null;
  filename: string;
  object_key: string;
  content_type: string | null;
  size_bytes: number | null;
  status: string;
  source: string | null;
  created_at: string | null;
  updated_at: string | null;
  metadata: Record<string, unknown> | null;
};
