import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export type BimStoreyWithSpaces = {
  id: string;
  global_id: string;
  name: string | null;
  elevation: number | null;
  spaces: Array<{
    id: string;
    global_id: string;
    name: string | null;
    raw_name: string | null;
    area: number | null;
    volume: number | null;
  }>;
};

export function BIMStructureSidebar({
  storeys,
  loading,
  error,
  onSpaceClick,
  onStoreyClick,
}: {
  storeys: BimStoreyWithSpaces[];
  loading: boolean;
  error: string | null;
  onSpaceClick: (globalId: string) => void;
  onStoreyClick: (globalIds: string[]) => void;
}) {
  const [expandedStoreyIds, setExpandedStoreyIds] = useState<Record<string, boolean>>({});
  const [selectedSpaceGlobalId, setSelectedSpaceGlobalId] = useState<string | null>(null);

  function toggleStorey(storeyGlobalId: string) {
    setExpandedStoreyIds((current) => ({
      ...current,
      [storeyGlobalId]: !current[storeyGlobalId],
    }));
  }

  return (
    <aside className="flex h-full w-96 flex-col border-l border-border bg-card">
      <div className="border-b border-border px-4 py-4">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-foreground">
          Building Structure
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">Storeys and spaces</p>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4">
        {loading ? (
          <div className="text-sm text-muted-foreground">Loading BIM structure...</div>
        ) : error ? (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        ) : storeys.length === 0 ? (
          <div className="text-sm text-muted-foreground">No storeys found.</div>
        ) : (
          <div className="space-y-3">
            {storeys.map((storey) => {
              const isExpanded = expandedStoreyIds[storey.global_id] ?? false;
              return (
                <div
                  key={storey.global_id}
                  data-global-id={storey.global_id}
                  className="rounded-lg border border-border bg-background"
                >
                  <button
                    type="button"
                    onClick={() => {
                      toggleStorey(storey.global_id);
                      const spaceGlobalIds = storey.spaces.map((space) => space.global_id);
                      console.log('[BIMStructureSidebar] storey click', {
                        storeyGlobalId: storey.global_id,
                        spaceGlobalIds,
                      });
                      onStoreyClick(spaceGlobalIds);
                    }}
                    className="flex w-full items-start justify-between gap-3 px-3 py-3 text-left"
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-foreground">
                        {storey.name ?? 'Unnamed storey'}
                      </div>
                      {storey.elevation !== null && (
                        <div className="mt-1 text-xs text-muted-foreground">
                          Elevation {storey.elevation}
                        </div>
                      )}
                    </div>
                    {isExpanded ? (
                      <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                  </button>

                  {isExpanded && (
                    <div className="border-t border-border px-2 py-2">
                      {storey.spaces.length === 0 ? (
                        <div className="px-2 py-2 text-sm text-muted-foreground">
                          No spaces
                        </div>
                      ) : (
                        <div className="space-y-1">
                          {storey.spaces.map((space) => {
                            const isSelected = selectedSpaceGlobalId === space.global_id;
                            return (
                              <Button
                                key={space.global_id}
                                type="button"
                                variant="ghost"
                                data-global-id={space.global_id}
                                className={cn(
                                  'h-auto w-full justify-start px-2 py-2 text-left',
                                  isSelected
                                    ? 'bg-muted text-foreground'
                                    : 'text-muted-foreground',
                                )}
                                onClick={() => {
                                  setSelectedSpaceGlobalId(space.global_id);
                                  console.log('[BIMStructureSidebar] space click', {
                                    spaceGlobalId: space.global_id,
                                  });
                                  onSpaceClick(space.global_id);
                                }}
                              >
                                <div className="min-w-0">
                                  <div className="truncate text-sm font-medium">
                                    {space.name ?? space.raw_name ?? space.global_id}
                                  </div>
                                  <div className="truncate text-xs opacity-80">
                                    Area {space.area ?? '--'} | Volume {space.volume ?? '--'}
                                  </div>
                                </div>
                              </Button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
}
