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

import { useEffect, useRef } from "react";
import { fetchBimStream } from "@/api/bim_files"; // your function
import { BIMViewerEngine } from "../BIMViewerEngine";

export default function BIMViewer({ bimId }: { bimId: string }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let engine: BIMViewerEngine | null = null;
    let cancelled = false;

    (async () => {
      if (!containerRef.current) return;

      const data = await fetchBimStream(bimId); // ArrayBuffer from FastAPI stream
      if (cancelled) return;

      engine = new BIMViewerEngine(containerRef.current);
      await engine.initIfcPipeline();
      if (cancelled) return;

      await engine.loadIFCFromArrayBuffer(data, `${bimId}.ifc`);
    })().catch((e) => console.error(e));

    return () => {
      cancelled = true;
      engine?.dispose();
    };
  }, [bimId]);

  return <div ref={containerRef} className="w-full h-full" />;
}
