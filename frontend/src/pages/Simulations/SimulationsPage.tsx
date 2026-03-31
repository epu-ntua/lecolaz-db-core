import { useEffect, useState } from "react";
import {
  getSimulationFileByDataset,
  listSimulationFiles,
  uploadSimulationFile,
} from "@/api/simulation_files";
import type { SimulationFileDto } from "@/types/api/simulations";
import { FileUpload } from "@/pages/DataDiscovery/components/FileUpload";
import { SimulationsFilesTable } from "@/pages/Simulations/components/SimulationsFilesTable";

const TERMINAL_STATUSES = new Set(["processed", "failed"]);

export default function SimulationsPage() {
  const [files, setFiles] = useState<SimulationFileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingDatasetIds, setPendingDatasetIds] = useState<string[]>([]);

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
    if (pendingDatasetIds.length === 0) {
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      const results = await Promise.allSettled(
        pendingDatasetIds.map(async (datasetId) => ({
          datasetId,
          simulation: await getSimulationFileByDataset(datasetId),
        })),
      );

      const nextPendingDatasetIds: string[] = [];

      results.forEach((result, index) => {
        if (result.status === "rejected") {
          nextPendingDatasetIds.push(pendingDatasetIds[index]);
          return;
        }

        const { datasetId, simulation } = result.value;
        if (TERMINAL_STATUSES.has(simulation.status ?? "")) {
          setFiles((current) =>
            current.map((row) =>
              row.dataset_id === datasetId
                ? simulation
                : row,
            ),
          );
          return;
        }

        if (simulation.status === "processing") {
        }
        setFiles((current) =>
          current.map((row) =>
            row.dataset_id === datasetId
              ? simulation
              : row,
          ),
        );
        nextPendingDatasetIds.push(datasetId);
      });

      setPendingDatasetIds(nextPendingDatasetIds);
    }, 1500);

    return () => window.clearTimeout(timeoutId);
  }, [pendingDatasetIds]);

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
            setPendingDatasetIds((current) =>
              current.includes(result.dataset_id)
                ? current
                : [...current, result.dataset_id],
            );
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
