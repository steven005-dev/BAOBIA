import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  webServer: {
    // Le serveur de développement relaie /api vers Django (le serveur preview ne le fait pas).
    command: 'npm run dev -- --host 127.0.0.1 --port 5174',
    port: 5174,
    env: { BAOBIA_API_TARGET: process.env.BAOBIA_API_TARGET ?? 'http://127.0.0.1:8000' },
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: 'http://localhost:5174',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'Mobile Android (Chrome)',
      use: {
        ...devices['Pixel 5'],
        channel: 'chrome',
      },
    },
  ],
})
