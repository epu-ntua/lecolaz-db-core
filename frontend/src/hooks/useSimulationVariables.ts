import { useEffect, useState } from 'react';
import { listSimulationVariablesByDataset } from '@/api/simulation_files';
import type { SimulationVariableDto } from '@/types/api/simulations';

export function useSimulationVariables(datasetId: string, enabled: boolean = true) {
  const [variables, setVariables] = useState<SimulationVariableDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !datasetId) {
      setVariables([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    listSimulationVariablesByDataset(datasetId)
      .then((rows) => {
        if (!cancelled) {
          setVariables(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load simulation variables');
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
  }, [datasetId, enabled]);

  return {
    variables,
    loading,
    error,
  };
}
