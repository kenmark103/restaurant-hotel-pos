import { Navigate, Route, Routes } from 'react-router-dom'

import { CustomerLoginPage } from '@/pages/CustomerLoginPage'
import { CustomerOverviewPage } from '@/pages/CustomerOverviewPage'

import { ProtectedRoute } from './ProtectedRoute'

export default function CustomerRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="login" replace />} />
      <Route path="login" element={<CustomerLoginPage />} />
      <Route
        path="overview"
        element={
          <ProtectedRoute audience="customer">
            <CustomerOverviewPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}
