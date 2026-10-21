import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Building2, Layers3, Maximize2 } from 'lucide-react';
import type { BimFileDto } from '@/types/api/bim';
import { Badge } from '@/components/ui/badge';
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
  const isProcessed = building.status === 'processed';

  return (
    <article className="group overflow-hidden rounded-2xl border bg-card shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-lg">
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
            className="relative h-full overflow-hidden bg-gradient-to-br from-accent via-secondary to-muted"
            aria-hidden="true"
          >
            <div className="absolute -right-10 -top-10 h-40 w-40 rounded-full border border-primary/10" />
            <div className="absolute bottom-[-18%] left-[12%] h-[82%] w-[68%] rotate-[-5deg] rounded-t-[2rem] border border-primary/15 bg-card/35 shadow-2xl" />
            <div className="absolute bottom-[14%] left-[28%] grid h-[45%] w-[42%] grid-cols-3 gap-2 opacity-50">
              {Array.from({ length: 9 }).map((_, index) => (
                <span
                  key={index}
                  className="rounded-sm border border-primary/20 bg-primary/10"
                />
              ))}
            </div>
            <Building2 className="absolute bottom-5 right-5 h-8 w-8 text-primary/55" />
          </div>
        )}
        <Badge
          variant={isProcessed ? 'default' : 'secondary'}
          className="absolute left-4 top-4 capitalize shadow-sm"
        >
          {building.status ?? 'Unknown'}
        </Badge>
      </div>

      <div className="p-5">
        <div className="min-w-0">
          <h2
            className="truncate text-xl font-semibold tracking-tight"
            title={buildingName(building.filename)}
          >
            {buildingName(building.filename)}
          </h2>
          <p
            className="mt-1 truncate text-xs text-muted-foreground"
            title={building.filename}
          >
            {building.filename}
          </p>
        </div>
        <div className="mt-5 flex flex-wrap gap-4 text-sm text-muted-foreground">
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
