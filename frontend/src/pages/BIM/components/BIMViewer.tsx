// src/pages/BIM/components/BIMViewer.tsx
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
