import { createBrowserRouter } from 'react-router-dom';
import { Activity, Blocks, FileBarChart } from 'lucide-react';
import AppLayout from './layout/AppLayout';
import AdministrationPage from '@/pages/Administration/AdministrationPage';
import BIMPage from '@/pages/BIM/BIMpage';
import BIMViewerPage from '@/pages/BIM/BIMViewerPage';
import DataDiscoveryPage from '@/pages/DataDiscovery/DataDiscoveryPage';
import NotFoundPage from '@/pages/NotFound/NotFoundPage';
import OverviewPage from '@/pages/Overview/OverviewPage';
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
      { path: 'buildings/:id', element: <BIMViewerPage /> },
      {
        path: 'components',
        element: (
          <PlaceholderPage
            title="Components"
            description="Browse the systems and assets that make up each building."
            icon={Blocks}
          />
        ),
      },
      {
        path: 'monitoring',
        element: (
          <PlaceholderPage
            title="Monitoring & Insights"
            description="A future home for live building status, signals and alerts."
            icon={Activity}
          />
        ),
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
