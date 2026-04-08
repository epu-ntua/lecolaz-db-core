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
    <div className="space-y-6">
      <header className="border-b border-border pb-4">
        <h1 className="text-2xl font-bold tracking-tight">Simulation files</h1>
        <p className="text-sm text-muted-foreground">
          Simulation records linked to uploaded files.
        </p>
      </header>

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
    </div>
  );
}
