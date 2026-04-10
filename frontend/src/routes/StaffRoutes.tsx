import { Navigate, Route, Routes } from 'react-router-dom'

import { StaffShell } from '@/layouts/StaffShell'
import { StaffActivatePage } from '@/pages/auth/StaffActivatePage'
import { StaffLoginPage } from '@/pages/auth/StaffLoginPage'
import { BranchesPage } from '@/pages/branches/BranchesPage'
import { DashboardPage } from '@/pages/dashboard/DashboardPage'
import { MenuPage } from '@/pages/menu/MenuPage'
import { OrdersPage } from '@/pages/orders/OrdersPage'
import { PosTerminalPage } from '@/pages/pos/PosTerminalPage'
import { SettingsPage } from '@/pages/settings/SettingsPage'
import { TablesPage } from '@/pages/tables/TablesPage'
import { TeamPage } from '@/pages/team/TeamPage'
import { ProtectedRoute } from './ProtectedRoute'

export default function StaffRoutes() {
  return (
    <Routes>
      {/* Login is always accessible - no shell, no protection */}
      <Route path="login" element={<StaffLoginPage />} />
      <Route path="activate" element={<StaffActivatePage />} />

      {/* Everything else is behind auth + StaffShell */}
      <Route
        element={
          <ProtectedRoute audience="staff">
            <StaffShell />
          </ProtectedRoute>
        }
      >
        <Route path="pos" element={<PosTerminalPage />} />
        <Route path="orders" element={<OrdersPage />} />
        <Route path="tables" element={<TablesPage />} />
        <Route path="settings" element={<SettingsPage />} />

        {/* Manager+ routes */}
        <Route
          path="dashboard"
          element={
            <ProtectedRoute audience="staff" roles={['admin', 'manager']}>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="menu"
          element={
            <ProtectedRoute audience="staff" roles={['admin', 'manager']}>
              <MenuPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="team"
          element={
            <ProtectedRoute audience="staff" roles={['admin', 'manager']}>
              <TeamPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="branches"
          element={
            <ProtectedRoute audience="staff" roles={['admin']}>
              <BranchesPage />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/staff/pos" replace />} />
      </Route>
    </Routes>
  )
}
