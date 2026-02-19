import { createBrowserRouter } from "react-router-dom";
import AppLayout from "./layout/AppLayout";
import AdminPage from "@/pages/Admin/AdminPage";
import AlertsPage from "@/pages/Alerts/AlertsPage";
import BIMPage from "@/pages/BIM/BIMpage";
import DashboardPage from "@/pages/Dashboard/DashboardPage";
import DataDiscoveryPage from "@/pages/DataDiscovery/DataDiscoveryPage";
import GovernancePage from "@/pages/GovernanceReporting/GovernancePage";
import NotFoundPage from "@/pages/NotFound/NotFoundPage";
import QueryingAnalyticsPage from "@/pages/QueryingAnalytics/QueryingAnalyticsPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: "admin", element: <AdminPage /> },
      { path: "alerts", element: <AlertsPage /> },
      { path: "bim", element: <BIMPage /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "data-discovery", element: <DataDiscoveryPage /> },
      { path: "governance-reporting", element: <GovernancePage /> },
      { path: "querying-analytics", element: <QueryingAnalyticsPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
]);
