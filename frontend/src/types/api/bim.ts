export type BimFileDto = {
  id: string;
  dataset_id: string;
  filename: string;
  format: string;
  status: string | null;
  schema: string | null;
  stats: {
    storeys?: number;
    spaces?: number;
    entities?: number;
  } | null;
  units: Array<Record<string, unknown>> | null;
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

export type BimStoreyDto = {
  id: string;
  bim_dataset_id: string;
  global_id: string;
  name: string | null;
  elevation: number | null;
  created_at: string | null;
};

export type BimSpaceDto = {
  id: string;
  bim_dataset_id: string;
  global_id: string;
  name: string | null;
  raw_name: string | null;
  storey_id: string | null;
  area: number | null;
  volume: number | null;
  created_at: string | null;
};
