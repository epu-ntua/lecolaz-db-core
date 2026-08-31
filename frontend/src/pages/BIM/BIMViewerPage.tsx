import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchBimMetadata, listBimSpaces, listBimStoreys } from '@/api/bim_files';
import { Button } from '@/components/ui/button';
import type { BimMetadataDto, BimSpaceDto, BimStoreyDto } from '@/types/api/bim';
import { BIMStructureSidebar } from './components/BIMStructureSidebar';
import BimViewer, { type BIMViewerHandle } from './components/BIMViewer';

export default function BIMViewerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [bim, setBim] = useState<BimMetadataDto | null>(null);
  const [storeys, setStoreys] = useState<BimStoreyDto[]>([]);
  const [spaces, setSpaces] = useState<BimSpaceDto[]>([]);
  const [structureLoading, setStructureLoading] = useState(true);
  const [structureError, setStructureError] = useState<string | null>(null);
  const viewerRef = useRef<BIMViewerHandle | null>(null);

  useEffect(() => {
    if (!id) return;

    fetchBimMetadata(id)
      .then(setBim)
      .catch(() => setBim(null));
  }, [id]);

  useEffect(() => {
    if (!id) {
      return;
    }

    let cancelled = false;
    setStructureLoading(true);
    setStructureError(null);

    Promise.all([listBimStoreys(id), listBimSpaces(id)])
      .then(([nextStoreys, nextSpaces]) => {
        if (cancelled) {
          return;
        }
        setStoreys(nextStoreys);
        setSpaces(nextSpaces);
      })
      .catch(() => {
        if (!cancelled) {
          setStoreys([]);
          setSpaces([]);
          setStructureError('Failed to load BIM structure.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setStructureLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  const structuredStoreys = useMemo(() => {
    const spacesByStoreyId = new Map<string, BimSpaceDto[]>();
    for (const space of spaces) {
      if (!space.storey_id) {
        continue;
      }
      const current = spacesByStoreyId.get(space.storey_id) ?? [];
      current.push(space);
      spacesByStoreyId.set(space.storey_id, current);
    }

    return storeys.map((storey) => ({
      id: storey.id,
      global_id: storey.global_id,
      name: storey.name,
      elevation: storey.elevation,
      spaces: spacesByStoreyId.get(storey.id) ?? [],
    }));
  }, [spaces, storeys]);

  if (!id) return null;

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 border-b">
        <Button variant="link" className="px-0" onClick={() => navigate('/bim')}>
          Back
        </Button>
        <h1 className="mt-2 text-lg font-semibold">Displaying: {bim?.filename ?? id}</h1>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <BimViewer ref={viewerRef} bimId={id} />
        </div>
        <BIMStructureSidebar
          storeys={structuredStoreys}
          loading={structureLoading}
          error={structureError}
          onSpaceClick={(globalId) => {
            console.log('[BIMViewerPage] forwarding space highlight', {
              globalId,
              hasViewerRef: Boolean(viewerRef.current),
            });
            void viewerRef.current?.highlightByGlobalIds([globalId]);
          }}
          onStoreyClick={(globalIds) => {
            console.log('[BIMViewerPage] forwarding storey highlight', {
              globalIds,
              hasViewerRef: Boolean(viewerRef.current),
            });
            void viewerRef.current?.highlightByGlobalIds(globalIds);
          }}
        />
      </div>
    </div>
  );
}
