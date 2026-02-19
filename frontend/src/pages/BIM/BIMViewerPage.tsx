import { useParams, useNavigate } from "react-router-dom";
import BimViewer from "./components/BIMViewer";

export default function BIMViewerPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  console.log("Route param id:", id);

  if (!id) return null;

  return (
    <div className="h-screen flex flex-col">
      <div className="p-4 border-b">
        <button
          onClick={() => navigate("/bim")}
          className="text-primary hover:underline"
        >
          ← Back
        </button>
      </div>

      <div className="flex-1">
        <BimViewer bimId={id} />
      </div>
    </div>
  );
}
