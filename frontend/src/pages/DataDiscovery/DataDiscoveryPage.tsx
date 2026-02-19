import { useState } from "react";
import { FileUpload } from "@/pages/DataDiscovery/components/FileUpload";
import { FilesTable } from "@/pages/DataDiscovery/components/FilesTable";

export default function DataDiscoveryPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">Uploaded files</h1>
        <p className="text-sm text-muted-foreground">
          Manage and monitor your platform assets.
        </p>
      </header>

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload onUploaded={() => setRefreshKey((k) => k + 1)} />
      </section>

      <section>
        <FilesTable refreshKey={refreshKey} />
      </section>
    </div>
  );
}