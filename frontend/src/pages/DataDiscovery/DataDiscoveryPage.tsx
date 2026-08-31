import { useEffect, useState } from 'react';
import { getDataset, listDatasets } from '@/api/datasets';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { DatasetDto } from '@/types/api/datasets';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';
import { FilesTable } from '@/pages/DataDiscovery/components/FilesTable';

export default function DataDiscoveryPage() {
  const [files, setFiles] = useState<DatasetDto[]>([]);
  const [loading, setLoading] = useState(true);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.id,
  });

  useEffect(() => {
    let cancelled = false;

    listDatasets()
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
      resolvedRows.forEach((dataset) => {
        const index = next.findIndex((row) => row.id === dataset.id);
        if (index >= 0) {
          next[index] = dataset;
        }
      });
      return next;
    });
    clearResolvedRows();
  }, [clearResolvedRows, resolvedRows]);

  return (
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">Uploaded files</h1>
        <p className="text-sm text-muted-foreground">
          Manage and monitor your platform assets.
        </p>
      </header>

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload
          onUploaded={async (result) => {
            const dataset = await getDataset(result.dataset_id);
            setFiles((current) => {
              const next = current.filter((row) => row.id !== dataset.id);
              return [dataset, ...next];
            });
            if (result.type === 'bim' || result.type === 'simulation') {
              queueDatasetId(result.dataset_id);
            }
          }}
        />
      </section>

      <section>
        <FilesTable files={files} loading={loading} />
      </section>
    </div>
  );
}
