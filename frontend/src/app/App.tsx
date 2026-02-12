import { useState } from 'react';
import { FileUpload } from '@/components/FileUpload';
import { FilesTable } from '@/components/FilesTable';
import { BIMFiles } from '@/components/BIMFiles';

function App() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    /* Add scrollbar-thin and overflow-y-auto here to apply it globally */
    <div className="min-h-screen h-screen overflow-y-auto bg-background text-foreground p-6 transition-colors duration-300 scrollbar-thin">
      <div className="max-max-5xl mx-auto space-y-6">
        
        <header className="border-b border-border pb-4">
          <h1 className="text-2xl font-bold tracking-tight">Uploaded files</h1>
          <p className="text-muted-foreground text-sm">
            Manage and monitor your platform assets.
          </p>
        </header>

        <main className="space-y-8">
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