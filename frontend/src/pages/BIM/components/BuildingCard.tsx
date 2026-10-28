import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, ImagePlus, Layers3, Maximize2, Pencil } from 'lucide-react';
import type { BimFileDto } from '@/types/api/bim';
import { StatusBadge } from '@/components/ui/status-badge';
import { BuildingIllustration } from '@/components/layout/BuildingIllustration';
import { Button } from '@/components/ui/button';
import { buildingName } from '@/lib/format';
import { getBimImageUrl } from '@/api/bim_files';

type BuildingCardProps = {
  building: BimFileDto;
  onDetails: () => void;
  onEditImage: () => void;
};

export function BuildingCard({ building, onDetails, onEditImage }: BuildingCardProps) {
  const [imageFailed, setImageFailed] = useState(false);
  const showImage = Boolean(building.image_object_key) && !imageFailed;
  useEffect(() => setImageFailed(false), [building.image_object_key]);

  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Details for ${buildingName(building.filename)}`}
      onClick={onDetails}
      onKeyDown={(event) => {
        if (
          event.target === event.currentTarget &&
          (event.key === 'Enter' || event.key === ' ')
        ) {
          event.preventDefault();
          onDetails();
        }
      }}
      className="group cursor-pointer overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:border-primary/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="relative aspect-[16/10] overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200">
        {showImage ? (
          <img
            src={`${getBimImageUrl(building.id)}?v=${encodeURIComponent(building.image_object_key ?? '')}`}
            alt=""
            className="h-full w-full object-contain p-3"
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
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="absolute right-3 top-3 border-white/80 bg-white/90 text-slate-700 shadow-sm backdrop-blur-sm hover:bg-white"
          onClick={(event) => {
            event.stopPropagation();
            onEditImage();
          }}
        >
          {building.image_object_key ? (
            <Pencil className="h-3.5 w-3.5" />
          ) : (
            <ImagePlus className="h-3.5 w-3.5" />
          )}
          {building.image_object_key ? 'Edit image' : 'Add image'}
        </Button>
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
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={(event) => {
                event.stopPropagation();
                onDetails();
              }}
            >
              Details
            </Button>
            <Button asChild size="sm">
              <Link
                to={`/buildings/${building.id}`}
                onClick={(event) => event.stopPropagation()}
              >
                View Building <ArrowUpRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </article>
  );
}
