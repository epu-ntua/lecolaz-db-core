import { useState } from "react";
import { uploadSimulationFile } from "@/api/simulation_files";
import { FileUpload } from "@/pages/DataDiscovery/components/FileUpload";
import { SimulationsFilesTable } from "@/pages/Simulations/components/SimulationsFilesTable";

export default function SimulationsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">Simulation files</h1>
        <p className="text-sm text-muted-foreground">
          Simulation records linked to uploaded files.
        </p>
      </header>

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload
          onUploaded={() => setRefreshKey((k) => k + 1)}
          uploadAction={uploadSimulationFile}
          accept=".eso"
          errorMessage="Simulation upload failed"
        />
      </section>

      <section>
        <SimulationsFilesTable refreshKey={refreshKey} />
      </section>
    </div>
  );
}
