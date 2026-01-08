import { useState } from "react";
import { FileUpload } from "./components/FileUpload";
import { FilesTable } from "./components/FilesTable";

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-5xl mx-auto space-y-4">
        <h1 className="text-xl font-semibold">Uploaded files</h1>

        <FileUpload onUploaded={() => setRefreshKey(k => k + 1)} />

        <FilesTable refreshKey={refreshKey} />
      </div>
    </div>
  );
}

export default App;
