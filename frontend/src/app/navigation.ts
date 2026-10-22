import {
  Activity,
  Blocks,
  Building2,
  Database,
  FileBarChart,
  LayoutDashboard,
  Settings,
  ChartNoAxesCombined,
} from 'lucide-react';

export const navigation = [
  { title: 'Overview', url: '/overview', icon: LayoutDashboard, group: 'Workspace' },
  { title: 'Buildings & Pilots', url: '/buildings', icon: Building2, group: 'Workspace' },
  { title: 'Components', url: '/components', icon: Blocks, group: 'Workspace' },
  {
    title: 'Monitoring & Performance',
    url: '/monitoring',
    icon: Activity,
    group: 'Workspace',
  },
  {
    title: 'Scenarios & Insights',
    url: '/scenarios',
    icon: ChartNoAxesCombined,
    group: 'Workspace',
  },
  { title: 'Data Explorer', url: '/data', icon: Database, group: 'Workspace' },
  {
    title: 'Validation & Reports',
    url: '/reports',
    icon: FileBarChart,
    group: 'Management',
  },
  {
    title: 'Administration',
    url: '/administration',
    icon: Settings,
    group: 'Management',
  },
];
