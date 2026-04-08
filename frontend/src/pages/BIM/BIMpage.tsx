import { useEffect, useState } from 'react';
import { getBimFileByDataset, listBimFiles, uploadBimFile } from '@/api/bim_files';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { BimFileDto } from '@/types/api/bim';
import { BIMFilesTable } from '@/pages/BIM/components/BIMFilesTable';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';

export default function BIMPage() {
  const [files, setFiles] = useState<BimFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getBimFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    let cancelled = false;

    listBimFiles()
      .then((rows) => {
        if (!cancelled) {
          setFiles(rows);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (resolvedRows.length === 0) {
      return;
    }

    setFiles((current) => {
      const next = [...current];
      resolvedRows.forEach((bim) => {
        const index = next.findIndex((row) => row.dataset_id === bim.dataset_id);
        if (index >= 0) {
          next[index] = bim;
        }
      });
      return next;
    });
    clearResolvedRows();
  }, [clearResolvedRows, resolvedRows]);

  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">BIM files</h1>
        <p className="text-sm text-muted-foreground">
          BIM records linked to uploaded files.
        </p>
      </header>

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload
          onUploaded={async (result) => {
            const bim = await getBimFileByDataset(result.dataset_id);
            setFiles((current) => {
              const next = current.filter((row) => row.id !== bim.id);
              return [bim, ...next];
            });
            queueDatasetId(result.dataset_id);
          }}
          uploadAction={uploadBimFile}
          accept=".ifc,.ifczip,.ifcxml"
          errorMessage="BIM upload failed"
        />
      </section>

      <section>
        <BIMFilesTable files={files} loading={loading} />
      </section>
    </div>
  );
}
