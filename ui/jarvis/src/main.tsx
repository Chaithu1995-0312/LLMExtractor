import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const queryClient = new QueryClient()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <div className="dark min-h-screen bg-background text-foreground font-sans">
        <App />
      </div>
    </QueryClientProvider>
  </React.StrictMode>,
)
