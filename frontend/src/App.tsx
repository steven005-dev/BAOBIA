import { RouterProvider } from 'react-router'

import { router } from '@/app/router'
import { AuthProvider } from '@/auth/AuthProvider'
import { ToastProvider } from '@/components/Toast'

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </AuthProvider>
  )
}
