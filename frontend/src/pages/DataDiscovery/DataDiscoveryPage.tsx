import { useEffect, useState } from "react";
import { getFile, listFiles } from "@/api/files";
import type { FileDto } from "@/types/api/files";
import { FileUpload } from "@/pages/DataDiscovery/components/FileUpload";
import { FilesTable } from "@/pages/DataDiscovery/components/FilesTable";

const TERMINAL_STATUSES = new Set(["processed", "failed"]);

export default function DataDiscoveryPage() {
  const [files, setFiles] = useState<FileDto[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingDatasetIds, setPendingDatasetIds] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    listFiles()
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
          dataset: await getFile(datasetId),
        })),
      );

      const nextPendingDatasetIds: string[] = [];

      results.forEach((result, index) => {
        if (result.status === "rejected") {
          nextPendingDatasetIds.push(pendingDatasetIds[index]);
          return;
        }

        const { datasetId, dataset } = result.value;
        if (TERMINAL_STATUSES.has(dataset.status)) {
          setFiles((current) =>
            current.map((row) => (row.id === datasetId ? dataset : row)),
          );
          return;
        }

        if (dataset.status === "processing") {
        }
        setFiles((current) =>
          current.map((row) => (row.id === datasetId ? dataset : row)),
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
        <h1 className="text-2xl font-bold tracking-tight">Uploaded files</h1>
        <p className="text-sm text-muted-foreground">
          Manage and monitor your platform assets.
        </p>
      </header>

      <section className="bg-card p-4 rounded-lg border border-border shadow-sm">
        <FileUpload
          onUploaded={async (result) => {
            const dataset = await getFile(result.dataset_id);
            setFiles((current) => {
              const next = current.filter((row) => row.id !== dataset.id);
              return [dataset, ...next];
            });
            if (result.type === "bim" || result.type === "simulation") {
              setPendingDatasetIds((current) =>
                current.includes(result.dataset_id)
                  ? current
                  : [...current, result.dataset_id],
              );
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
