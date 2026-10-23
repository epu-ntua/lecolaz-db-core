import { useState } from 'react';
import { Blocks, Leaf, Recycle, RefreshCw } from 'lucide-react';
import { getComponentFileUrl } from '@/api/components';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { COMPONENT_CLASS_LABELS } from '@/lib/constants';
import type { ModularComponentDto } from '@/types/api/components';

type ComponentCardProps = {
  component: ModularComponentDto;
  onDetails: () => void;
};

export function ComponentCard({ component, onDetails }: ComponentCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(component.photo_object_key) && !imageFailed;
  const dpp = component.dpp;
  const carbon = dpp?.transparency?.environmental?.carbon_footprint?.total_kg_co2eq;

  return (
    <article className="group overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:border-primary/30 hover:shadow-md">
      <div className="relative aspect-[16/10] overflow-hidden bg-muted">
        {showImage ? (
          <img
            src={getComponentFileUrl(component.id, 'photo')}
            alt=""
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div
            className="blueprint flex h-full items-center justify-center bg-accent/60"
            aria-hidden="true"
          >
            <Blocks className="h-12 w-12 text-primary/60" />
          </div>
        )}
        <div className="absolute left-4 top-4 rounded-full bg-card">
          <Badge>{COMPONENT_CLASS_LABELS[component.component_class]}</Badge>
        </div>
      </div>

      <div className="p-5">
        <div className="min-w-0">
          <h3
            className="truncate text-lg font-semibold tracking-tight"
            title={component.name}
          >
            {component.name}
          </h3>
          <p className="mt-1 truncate text-xs text-muted-foreground">
            {dpp?.traceability?.product_id?.serial_number ?? '--'}
          </p>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5 capitalize">
            <RefreshCw className="h-4 w-4 text-primary" />
            {dpp?.traceability?.lifecycle_stage?.value ?? '--'}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Recycle className="h-4 w-4 text-primary" />
            {dpp?.transparency?.material?.circularity_class ?? '--'}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Leaf className="h-4 w-4 text-primary" />
            {typeof carbon === 'number' ? `${carbon} kgCO₂e` : '--'}
          </span>
        </div>
        <div className="mt-5 flex items-center justify-end border-t pt-4">
          <Button type="button" size="sm" variant="ghost" onClick={onDetails}>
            Details
          </Button>
        </div>
      </div>
    </article>
  );
}
