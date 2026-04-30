import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Process from '../views/MainView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationRunView from '../views/SimulationRunView.vue'
import ReportView from '../views/ReportView.vue'
import InteractionView from '../views/InteractionView.vue'
import CreativeTestView from '../views/CreativeTestView.vue'
import ClientWorkspace from '../views/ClientWorkspace.vue'
import OverviewTab from '../views/client/OverviewTab.vue'
import ContextTab from '../views/client/ContextTab.vue'
import CreativeTestsTab from '../views/client/CreativeTestsTab.vue'
import TestDetailTab from '../views/client/TestDetailTab.vue'
import ReportsTab from '../views/client/ReportsTab.vue'
import SimsTab from '../views/client/SimsTab.vue'
import SettingsTab from '../views/client/SettingsTab.vue'
import GraphFullscreenTab from '../views/client/GraphFullscreenTab.vue'
import Manual from '../views/Manual.vue'
import Help from '../views/Help.vue'
import Guide from '../views/Guide.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  // Legacy simulation/report flow — still reachable from old links.
  {
    path: '/process/:projectId',
    name: 'Process',
    component: Process,
    props: true
  },
  {
    path: '/simulation/:simulationId',
    name: 'Simulation',
    component: SimulationView,
    props: true
  },
  {
    path: '/simulation/:simulationId/start',
    name: 'SimulationRun',
    component: SimulationRunView,
    props: true
  },
  {
    path: '/report/:reportId',
    name: 'Report',
    component: ReportView,
    props: true
  },
  {
    path: '/interaction/:reportId',
    name: 'Interaction',
    component: InteractionView,
    props: true
  },
  {
    path: '/creative-test',
    name: 'CreativeTest',
    component: CreativeTestView
  },
  // R2.2: /clients now redirects to the cliente-céntrica home.
  { path: '/clients', redirect: '/' },
  // Always-on usage docs reachable from the Sidebar global section.
  { path: '/guide',  name: 'Guide',  component: Guide },
  { path: '/manual', name: 'Manual', component: Manual },
  { path: '/help',   name: 'Help',   component: Help },
  // R2.3: client workspace — TopNav + Sidebar + tab content (router-view).
  {
    path: '/clients/:clientId',
    component: ClientWorkspace,
    props: true,
    children: [
      { path: '', redirect: { name: 'ClientOverview' } },
      { path: 'overview', name: 'ClientOverview', component: OverviewTab },
      { path: 'context',  name: 'ClientContext',  component: ContextTab },
      { path: 'tests',    name: 'ClientTests',    component: CreativeTestsTab },
      { path: 'tests/:testId', name: 'ClientTestDetail', component: TestDetailTab },
      { path: 'reports',  name: 'ClientReports',  component: ReportsTab },
      { path: 'sims',     name: 'ClientSims',     component: SimsTab },
      { path: 'settings', name: 'ClientSettings', component: SettingsTab },
      { path: 'graph',    name: 'ClientGraph',    component: GraphFullscreenTab }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
