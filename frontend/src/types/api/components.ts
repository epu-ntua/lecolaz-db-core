export type ComponentClass = 'FacadeElement' | 'InteriorWall' | 'FloorCovering';

export type ComponentFileKind = 'photo' | 'qr' | 'ifc';

// Draft DPP (v0.2): every field is optional so schema changes do not break the UI.
export type DppMaterial = {
  name?: string;
  weight_kg?: number;
  recycled_content_pct?: number;
};

export type Dpp = {
  '@id'?: string;
  traceability?: {
    product_id?: {
      product_name?: string;
      product_type?: string;
      serial_number?: string;
      production_date?: string;
    };
    manufacturer?: {
      name?: string;
      country?: string;
    };
    lifecycle_stage?: {
      value?: string;
      last_update?: string;
    };
    reuse_cycles?: {
      value?: number;
    };
  };
  transparency?: {
    material?: {
      materials?: DppMaterial[];
      circularity_class?: string;
    };
    environmental?: {
      carbon_footprint?: {
        total_kg_co2eq?: number;
        performance_class?: string;
      };
    };
    technical?: {
      dimensions?: {
        width_m?: number;
        height_m?: number;
        thickness_m?: number;
      };
      fire_reaction_class?: string;
      expected_lifetime_years?: number;
      disassembly?: {
        connection_type?: string;
        reversible?: boolean;
      };
      end_of_life_scenario?: string;
    };
  };
  trust?: {
    epd?: {
      epd_id?: string;
      valid_until?: string;
    };
  };
  meta?: {
    schema_version?: string;
    status?: string;
  };
};

export type ModularComponentDto = {
  id: string;
  name: string;
  component_class: ComponentClass;
  bim_dataset_id: string | null;
  dpp: Dpp | null;
  photo_object_key: string | null;
  qr_object_key: string | null;
  ifc_object_key: string | null;
  created_at: string | null;
};
