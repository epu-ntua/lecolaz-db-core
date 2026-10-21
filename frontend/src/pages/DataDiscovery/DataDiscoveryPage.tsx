import { useEffect, useState } from 'react';
import { getDataset, listDatasets } from '@/api/datasets';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { DatasetDto } from '@/types/api/datasets';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';
import { FilesTable } from '@/pages/DataDiscovery/components/FilesTable';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';

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
    <PageContainer className="space-y-8">
      <PageHeader
        eyebrow="Workspace"
        title="Data Explorer"
        description="Manage uploaded files and follow their processing status."
      />

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
    </PageContainer>
  );
}
