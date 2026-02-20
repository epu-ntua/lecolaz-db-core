import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchBimMetadata } from "@/api/bim_files";
import type { BimMetadataDto } from "@/types/api/bim";
import BimViewer from "./components/BIMViewer";

export default function BIMViewerPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [bim, setBim] = useState<BimMetadataDto | null>(null);

  useEffect(() => {
    if (!id) return;

    fetchBimMetadata(id)
      .then(setBim)
      .catch(() => setBim(null));
  }, [id]);

  if (!id) return null;

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 border-b">
        <button
          onClick={() => navigate("/bim")}
          className="text-primary hover:underline"
        >
          Back
        </button>
        <h1 className="mt-2 text-lg font-semibold">Displaying: {bim?.filename ?? id}</h1>
      </div>

      <div className="flex-1">
        <BimViewer bimId={id} />
      </div>
    </div>
  );
}
