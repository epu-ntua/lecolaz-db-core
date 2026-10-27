import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Layers3, Maximize2 } from 'lucide-react';
import type { BimFileDto } from '@/types/api/bim';
import { StatusBadge } from '@/components/ui/status-badge';
import { BuildingIllustration } from '@/components/layout/BuildingIllustration';
import { Button } from '@/components/ui/button';

type BuildingCardProps = {
  building: BimFileDto;
  coverImageUrl?: string;
  onDetails: () => void;
};

const buildingName = (filename: string) =>
  filename.replace(/\.(ifc|ifczip|ifcxml)$/i, '').replace(/[_-]+/g, ' ');

export function BuildingCard({ building, coverImageUrl, onDetails }: BuildingCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(coverImageUrl) && !imageFailed;

  return (
    <article className="group overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:border-primary/30 hover:shadow-md">
      <div className="relative aspect-[16/10] overflow-hidden bg-muted">
        {showImage ? (
          <img
            src={coverImageUrl}
            alt=""
            className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div
            className="blueprint flex h-full items-center justify-center bg-accent/60"
            aria-hidden="true"
          >
            <BuildingIllustration className="h-full w-full p-5 transition-transform duration-300 group-hover:scale-[1.03]" />
            <span className="absolute bottom-3 left-4 text-[10px] uppercase tracking-[0.18em] text-primary/70">
              Digital building model
            </span>
          </div>
        )}
        <div className="absolute left-4 top-4 flex rounded-md bg-card">
          <StatusBadge status={building.status} />
        </div>
      </div>

      <div className="p-5">
        <div className="min-w-0">
          <h3
            className="truncate text-lg font-semibold tracking-tight"
            title={buildingName(building.filename)}
          >
            {buildingName(building.filename)}
          </h3>
          <p
            className="mt-1 truncate text-xs text-muted-foreground"
            title={building.filename}
          >
            {building.filename}
          </p>
        </div>
        <div className="mt-4 flex flex-wrap gap-4 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Layers3 className="h-4 w-4 text-primary" />
            {building.stats?.storeys ?? '—'} storeys
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Maximize2 className="h-4 w-4 text-primary" />
            {building.stats?.spaces ?? '—'} spaces
          </span>
        </div>
        <div className="mt-5 flex items-center justify-between border-t pt-4">
          <p className="text-xs text-muted-foreground">
            {building.schema ?? building.format.toUpperCase()}
          </p>
          <div className="flex gap-2">
            <Button type="button" size="sm" variant="ghost" onClick={onDetails}>
              Details
            </Button>
            <Button asChild size="sm">
              <Link to={`/buildings/${building.id}`}>
                Open <ArrowUpRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
