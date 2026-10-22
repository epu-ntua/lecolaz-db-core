// src/pages/BIM/components/BIMViewer.tsx
/**
 * BIMViewer (React Component)
 * ----------------------------
 * This component acts as the bridge between React and the 3D rendering engine.
 *
 * Responsibilities:
 * - Receives a BIM file ID as a prop
 * - Fetches the IFC file stream from the backend (ArrayBuffer)
 * - Instantiates the BIMViewerEngine with the container DOM element
 * - Initializes the IFC rendering pipeline
 * - Loads the IFC model into the 3D scene
 * - Disposes the engine properly on unmount
 *
 * Important:
 * - This component does NOT contain any 3D logic.
 * - All rendering and IFC processing are delegated to BIMViewerEngine.
 * - React is only responsible for lifecycle management and data fetching.
 */

import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { ErrorNotice, LoadingState } from '@/components/layout/Feedback';
import { Button } from '@/components/ui/button';
import { Focus } from 'lucide-react';
import { fetchBimStream } from '@/api/bim_files'; // your function
import { BIMViewerEngine } from '../BIMViewerEngine';

export type BIMViewerHandle = {
  highlightByGlobalIds: (globalIds: string[]) => Promise<void>;
};

const BIMViewer = forwardRef<BIMViewerHandle, { bimId: string }>(function BIMViewer(
  { bimId },
  ref,
) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const engineRef = useRef<BIMViewerEngine | null>(null);

  useImperativeHandle(ref, () => ({
    async highlightByGlobalIds(globalIds: string[]) {
      await engineRef.current?.highlightByGlobalIds(globalIds);
    },
  }));

  useEffect(() => {
    let engine: BIMViewerEngine | null = null;
    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      if (!containerRef.current) return;

      const data = await fetchBimStream(bimId); // ArrayBuffer from FastAPI stream
      if (cancelled) return;

      engine = new BIMViewerEngine(containerRef.current);
      engineRef.current = engine;

      await engine.initIfcPipeline();
      if (cancelled) return;

      await engine.loadIFCFromArrayBuffer(data, `${bimId}.ifc`);
    })()
      .then(() => {
        if (!cancelled) setLoading(false);
      })
      .catch(() => {
        if (!cancelled) {
          setLoading(false);
          setError(
            'The 3D model could not be loaded. Check that processing has completed and try again.',
          );
        }
      });

    return () => {
      cancelled = true;
      engineRef.current = null;
      engine?.dispose();
    };
  }, [bimId, retry]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {!loading && !error && (
        <>
          <Button
            variant="outline"
            size="sm"
            className="absolute right-4 top-4 shadow-sm"
            onClick={() => {
              void engineRef.current
                ?.fitModel()
                .catch(() =>
                  setError(
                    'The view could not be reset. Reload the model and try again.',
                  ),
                );
            }}
          >
            <Focus className="h-4 w-4" /> Reset view
          </Button>
          <p className="pointer-events-none absolute bottom-4 left-4 rounded-lg border bg-card/95 px-3 py-2 text-[11px] text-muted-foreground">
            Drag to orbit · Scroll to zoom
          </p>
        </>
      )}
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/90">
          <LoadingState label="Preparing your 3D model…" />
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/95 p-6">
          <ErrorNotice message={error} onRetry={() => setRetry((value) => value + 1)} />
        </div>
      )}
    </div>
  );
});

export default BIMViewer;
