import { useEffect, useState } from 'react';
import {
  getSimulationFileByDataset,
  listSimulationFiles,
  uploadSimulationFile,
} from '@/api/simulation_files';
import { usePendingDatasetPolling } from '@/hooks/usePendingDatasetPolling';
import type { SimulationFileDto } from '@/types/api/simulations';
import { FileUpload } from '@/pages/DataDiscovery/components/FileUpload';
import { SimulationsFilesTable } from '@/pages/Simulations/components/SimulationsFilesTable';
import { PageContainer } from '@/components/layout/PageContainer';
import { PageHeader } from '@/components/layout/PageHeader';

export default function SimulationsPage() {
  const [files, setFiles] = useState<SimulationFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const { resolvedRows, clearResolvedRows, queueDatasetId } = usePendingDatasetPolling({
    fetchByDatasetId: getSimulationFileByDataset,
    getStatus: (row) => row.status,
    getDatasetId: (row) => row.dataset_id,
  });

  useEffect(() => {
    let cancelled = false;

    listSimulationFiles()
      .then((rows) => {
        if (!cancelled) {
          setFiles(rows);
          rows.forEach((row) => {
            if (row.status !== 'processed' && row.status !== 'failed') {
              queueDatasetId(row.dataset_id);
            }
          });
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
  }, [queueDatasetId]);

  useEffect(() => {
    if (resolvedRows.length === 0) {
      return;
    }

    setFiles((current) => {
      const next = [...current];
      resolvedRows.forEach((simulation) => {
        const index = next.findIndex((row) => row.dataset_id === simulation.dataset_id);
        if (index >= 0) {
          next[index] = simulation;
        }
      });
      return next;
    });
    clearResolvedRows();
  }, [clearResolvedRows, resolvedRows]);

  return (
    <PageContainer className="space-y-8">
      <PageHeader
        eyebrow="Scenarios & Performance"
        title="Simulation files"
        description="Manage simulation records and inspect their processed outputs."
      />

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload
          onUploaded={async (result) => {
            const simulation = await getSimulationFileByDataset(result.dataset_id);
            setFiles((current) => {
              const next = current.filter((row) => row.id !== simulation.id);
              return [simulation, ...next];
            });
            queueDatasetId(result.dataset_id);
          }}
          uploadAction={uploadSimulationFile}
          accept=".eso"
          errorMessage="Simulation upload failed"
        />
      </section>

      <section>
        <SimulationsFilesTable files={files} loading={loading} />
      </section>
    </PageContainer>
  );
}
