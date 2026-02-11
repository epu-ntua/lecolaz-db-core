import { useState } from 'react';
import { FileUpload } from '@/components/FileUpload';
import { FilesTable } from '@/components/FilesTable';
import { BIMFiles } from '@/components/BIMFiles';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    /* 1. Use bg-background for your Warm Sand and text-foreground for Forest Green */
    <div className="min-h-screen bg-background text-foreground p-6 transition-colors duration-300">
      <div className="max-w-5xl mx-auto space-y-6">
        
        {/* 2. Using font-bold and tracking-tight makes brand titles look more premium */}
        <header className="border-b border-border pb-4">
          <h1 className="text-2xl font-bold tracking-tight">Uploaded files</h1>
          <p className="text-muted-foreground text-sm">
            Manage and monitor your platform assets.
          </p>
        </header>

        <main className="space-y-8">
          {/* FileUpload now uses your brand primary (Forest Green) button */}
          <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
             <FileUpload onUploaded={() => setRefreshKey((k) => k + 1)} />
          </section>

          <section>
            <FilesTable refreshKey={refreshKey} />
          </section>

          <section className="space-y-3">
            <header>
              <h2 className="text-lg font-semibold tracking-tight">BIM files</h2>
              <p className="text-sm text-muted-foreground">
                BIM records linked to uploaded files.
              </p>
            </header>
            <BIMFiles refreshKey={refreshKey} />
          </section>
        </main>

      </div>
    </div>
  );
}

export default App;
