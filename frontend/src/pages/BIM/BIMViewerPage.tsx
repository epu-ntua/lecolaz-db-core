import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import {
  fetchBimMetadata,
  fetchBimStream,
  listBimSpaces,
  listBimStoreys,
} from '@/api/bim_files';
import { fetchComponentIfc, getComponent } from '@/api/components';
import { ArrowLeft, Layers3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { BimMetadataDto, BimSpaceDto, BimStoreyDto } from '@/types/api/bim';
import { BIMStructureSidebar } from './components/BIMStructureSidebar';
import BimViewer, { type BIMViewerHandle } from './components/BIMViewer';

export default function BIMViewerPage() {
  const { id } = useParams();
  const isComponent = useLocation().pathname.startsWith('/components/');
  const [componentName, setComponentName] = useState<string | null>(null);
  const [showStructure, setShowStructure] = useState(false);
  const navigate = useNavigate();
  const [bim, setBim] = useState<BimMetadataDto | null>(null);
  const [storeys, setStoreys] = useState<BimStoreyDto[]>([]);
  const [spaces, setSpaces] = useState<BimSpaceDto[]>([]);
  const [structureLoading, setStructureLoading] = useState(true);
  const [structureError, setStructureError] = useState<string | null>(null);
  const viewerRef = useRef<BIMViewerHandle | null>(null);

  useEffect(() => {
    if (!id || isComponent) return;

    fetchBimMetadata(id)
      .then(setBim)
      .catch(() => setBim(null));
  }, [id, isComponent]);

  useEffect(() => {
    if (!id || !isComponent) return;
    getComponent(id)
      .then((component) => setComponentName(component.name))
      .catch(() => setComponentName(null));
  }, [id, isComponent]);

  useEffect(() => {
    if (!id || isComponent) {
      setStructureLoading(false);
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
  }, [id, isComponent]);

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
    <div className="flex h-full min-h-[480px] flex-col bg-card">
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <Button
          variant="ghost"
          size="icon"
          aria-label={isComponent ? 'Back to components' : 'Back to buildings'}
          onClick={() => navigate(isComponent ? '/components' : '/buildings')}
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {isComponent ? 'Component viewer' : 'BIM viewer'}
          </p>
          <h1 className="truncate text-base font-semibold">
            {isComponent ? (componentName ?? id) : (bim?.filename ?? id)}
          </h1>
        </div>
        <Button
          variant="outline"
          size="sm"
          className={isComponent ? 'hidden' : 'xl:hidden'}
          aria-expanded={showStructure}
          onClick={() => setShowStructure(!showStructure)}
        >
          <Layers3 className="h-4 w-4" /> Structure
        </Button>
      </div>

      <div className="relative flex min-h-0 flex-1">
        <div className="min-w-0 flex-1">
          <BimViewer
            ref={viewerRef}
            sourceId={id}
            fetchStream={isComponent ? fetchComponentIfc : fetchBimStream}
          />
        </div>
        <div
          className={
            isComponent
              ? 'hidden'
              : showStructure
                ? 'absolute inset-y-0 right-0 z-10 w-[min(320px,100%)] shadow-xl xl:static xl:shadow-none'
                : 'hidden w-80 xl:block'
          }
        >
          <BIMStructureSidebar
            storeys={structuredStoreys}
            loading={structureLoading}
            error={structureError}
            onSpaceClick={(globalId) => {
              void viewerRef.current?.highlightByGlobalIds([globalId]);
            }}
            onStoreyClick={(globalIds) => {
              void viewerRef.current?.highlightByGlobalIds(globalIds);
            }}
          />
        </div>
      </div>
    </div>
  );
}
