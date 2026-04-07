import { Route, Routes } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { HomePage } from './pages/HomePage'
import { CustomerLoginPage } from './pages/CustomerLoginPage'
import { CustomerOverviewPage } from './pages/CustomerOverviewPage'
import { StaffDashboardPage } from './pages/StaffDashboardPage'
import { StaffLoginPage } from './pages/StaffLoginPage'
import { ProtectedRoute } from './routes/ProtectedRoute'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<HomePage />} />
        <Route path="/staff/login" element={<StaffLoginPage />} />
        <Route
          path="/staff/dashboard"
          element={
            <ProtectedRoute audience="staff">
              <StaffDashboardPage />
            </ProtectedRoute>
          }
        />
        <Route path="/account/login" element={<CustomerLoginPage />} />
        <Route
          path="/account/overview"
          element={
            <ProtectedRoute audience="customer">
              <CustomerOverviewPage />
            </ProtectedRoute>
          }
        />
      </Route>
    </Routes>
  )
}
