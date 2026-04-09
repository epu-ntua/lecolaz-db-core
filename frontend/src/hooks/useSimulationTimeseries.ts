import { useEffect, useState } from 'react';
import { listSimulationTimeseries } from '@/api/simulation_files';
import type { SimulationTimeseriesPointDto } from '@/types/api/simulations';

export function useSimulationTimeseries(
  simulationId: string,
  variableId: string | null,
  enabled: boolean = true,
) {
  const [points, setPoints] = useState<SimulationTimeseriesPointDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || !simulationId || !variableId) {
      setPoints([]);
      setLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    listSimulationTimeseries(simulationId, variableId)
      .then((rows) => {
        if (!cancelled) {
          setPoints(rows);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Failed to load simulation timeseries');
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
  }, [enabled, simulationId, variableId]);

  return {
    points,
    loading,
    error,
  };
}
