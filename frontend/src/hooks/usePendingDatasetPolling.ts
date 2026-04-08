import { useCallback, useEffect, useState } from 'react';

const DEFAULT_TERMINAL_STATUSES = new Set(['processed', 'failed']);

type FetchByDatasetId<T> = (datasetId: string) => Promise<T>;
type GetStatus<T> = (row: T) => string | null | undefined;
type GetDatasetId<T> = (row: T) => string;

type UsePendingDatasetPollingParams<T> = {
  fetchByDatasetId: FetchByDatasetId<T>;
  getStatus: GetStatus<T>;
  getDatasetId: GetDatasetId<T>;
  pollMs?: number;
  terminalStatuses?: Set<string>;
};

export function usePendingDatasetPolling<T>({
  fetchByDatasetId,
  getStatus,
  getDatasetId,
  pollMs = 1500,
  terminalStatuses = DEFAULT_TERMINAL_STATUSES,
}: UsePendingDatasetPollingParams<T>) {
  const [pendingDatasetIds, setPendingDatasetIds] = useState<string[]>([]);
  const [resolvedRows, setResolvedRows] = useState<T[]>([]);

  useEffect(() => {
    if (pendingDatasetIds.length === 0) {
      return;
    }

    const timeoutId = window.setTimeout(async () => {
      const results = await Promise.allSettled(
        pendingDatasetIds.map(async (datasetId) => ({
          datasetId,
          row: await fetchByDatasetId(datasetId),
        })),
      );

      const nextPendingDatasetIds: string[] = [];
      const resolvedRows: T[] = [];

      results.forEach((result, index) => {
        if (result.status === 'rejected') {
          nextPendingDatasetIds.push(pendingDatasetIds[index]);
          return;
        }

        const { datasetId, row } = result.value;
        resolvedRows.push(row);

        if (!terminalStatuses.has(getStatus(row) ?? '')) {
          nextPendingDatasetIds.push(datasetId);
        }
      });

      setPendingDatasetIds(nextPendingDatasetIds);
      setResolvedRows((current) => [...current, ...resolvedRows]);
    }, pollMs);

    return () => window.clearTimeout(timeoutId);
  }, [fetchByDatasetId, getStatus, pendingDatasetIds, pollMs, terminalStatuses]);

  const clearResolvedRows = useCallback(() => {
    setResolvedRows([]);
  }, []);

  const queueDatasetId = useCallback((datasetId: string) => {
    setPendingDatasetIds((current) =>
      current.includes(datasetId) ? current : [...current, datasetId],
    );
  }, []);

  const dedupedResolvedRows = (() => {
    const deduped = new Map<string, T>();
    resolvedRows.forEach((row) => {
      deduped.set(getDatasetId(row), row);
    });
    return Array.from(deduped.values());
  })();

  return {
    resolvedRows: dedupedResolvedRows,
    clearResolvedRows,
    queueDatasetId,
  };
}
