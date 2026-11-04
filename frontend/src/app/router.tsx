import { createBrowserRouter } from 'react-router-dom';
import { FileBarChart } from 'lucide-react';
import AppLayout from './layout/AppLayout';
import AdministrationPage from '@/pages/Administration/AdministrationPage';
import BIMPage from '@/pages/BIM/BIMpage';
import ComponentsPage from '@/pages/Components/ComponentsPage';

import DataDiscoveryPage from '@/pages/DataDiscovery/DataDiscoveryPage';
import NotFoundPage from '@/pages/NotFound/NotFoundPage';
import OverviewPage from '@/pages/Overview/OverviewPage';
import MonitoringPage from '@/pages/Monitoring/MonitoringPage';
import PlaceholderPage from '@/pages/Placeholder/PlaceholderPage';
import ScenariosPage from '@/pages/Simulations/ScenariosPage';
import SimulationDetailsPage from '@/pages/Simulations/SimulationDetailsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'overview', element: <OverviewPage /> },
      { path: 'buildings', element: <BIMPage /> },
      {
        path: 'buildings/:id',
        lazy: async () => ({
          Component: (await import('@/pages/BIM/BIMViewerPage')).default,
        }),
      },
      { path: 'components', element: <ComponentsPage /> },
      {
        path: 'components/:id/view',
        lazy: async () => ({
          Component: (await import('@/pages/BIM/BIMViewerPage')).default,
        }),
      },
      {
        path: 'monitoring',
        element: <MonitoringPage />,
      },
      {
        path: 'scenarios',
        element: <ScenariosPage />,
      },
      { path: 'data', element: <DataDiscoveryPage /> },
      { path: 'data/simulations/:id', element: <SimulationDetailsPage /> },
      {
        path: 'reports',
        element: (
          <PlaceholderPage
            title="Validation & Reports"
            description="Prepare clear summaries of building and portfolio performance."
            icon={FileBarChart}
          />
        ),
      },
      {
        path: 'administration',
        element: <AdministrationPage />,
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
