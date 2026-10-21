import { useEffect, useState } from 'react';
import { Building2, Upload } from 'lucide-react';
import { getBimFileByDataset, listBimFiles, uploadBimFile } from '@/api/bim_files';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { BimFileDto } from '@/types/api/bim';
import { BIMDetailsDialog } from './components/BIMDetailsDialog';
import { BuildingCard } from './components/BuildingCard';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';

export default function BIMPage() {
  const [files, setFiles] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<BimFileDto | null>(null);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getBimFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    let cancelled = false;
    listBimFiles()
      .then((rows) => {
        if (!cancelled) setFiles(rows);
      })
      .catch(() => {
        if (!cancelled) setError('Buildings could not be loaded. Please try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resolvedRows.length === 0) return;
    setFiles((current) => {
      const next = [...current];
      resolvedRows.forEach((bim) => {
        const index = next.findIndex((row) => row.dataset_id === bim.dataset_id);
        if (index >= 0) next[index] = bim;
      });
      return next;
    });
    clearResolvedRows();
  }, [clearResolvedRows, resolvedRows]);

  return (
    <PageContainer size="wide" className="space-y-8">
      <PageHeader
        eyebrow="Portfolio"
        title="Buildings & Pilots"
        description="Explore your building models, open the BIM viewer and manage the source files behind each digital asset."
      />

      <section className="rounded-2xl border bg-card p-4 shadow-sm sm:flex sm:items-center sm:justify-between sm:gap-6 sm:p-5">
        <div className="mb-4 flex items-center gap-3 sm:mb-0">
          <div className="rounded-xl bg-accent p-3 text-accent-foreground">
            <Upload className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold">Add a building model</h2>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Upload IFC, IFCZIP or IFCXML files.
            </p>
          </div>
        </div>
        <FileUpload
          onUploaded={async (result) => {
            const bim = await getBimFileByDataset(result.dataset_id);
            setFiles((current) => [bim, ...current.filter((row) => row.id !== bim.id)]);
            queueDatasetId(result.dataset_id);
          }}
          uploadAction={uploadBimFile}
          accept=".ifc,.ifczip,.ifcxml"
          errorMessage="BIM upload failed"
        />
      </section>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <section>
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold tracking-tight">Building portfolio</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {loading
                ? 'Loading buildings…'
                : `${files.length} ${files.length === 1 ? 'building' : 'buildings'}`}
            </p>
          </div>
        </div>
        {loading ? (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div
                key={index}
                className="aspect-[4/3] animate-pulse rounded-2xl border bg-muted"
              />
            ))}
          </div>
        ) : files.length === 0 ? (
          <div className="flex min-h-80 flex-col items-center justify-center rounded-2xl border border-dashed bg-card/70 p-8 text-center">
            <div className="mb-4 rounded-2xl bg-accent p-4 text-accent-foreground">
              <Building2 className="h-7 w-7" />
            </div>
            <h3 className="text-lg font-semibold">Your building portfolio starts here</h3>
            <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
              Upload a BIM model above. It will appear here as soon as processing begins.
            </p>
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {files.map((file) => (
              <BuildingCard
                key={file.id}
                building={file}
                onDetails={() => setSelectedFile(file)}
              />
            ))}
          </div>
        )}
      </section>

      {selectedFile && (
        <BIMDetailsDialog file={selectedFile} onClose={() => setSelectedFile(null)} />
      )}
    </PageContainer>
  );
}
