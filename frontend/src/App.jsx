
import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import SetupWizard from './components/SetupWizard'
import ErrorBoundary from './components/ErrorBoundary'
import UpdateBanner from './components/UpdateBanner'
import Dashboard from './pages/Dashboard'
import FindLeads from './pages/FindLeads'
import ManageLeads from './pages/ManageLeads'
import EmailStudio from './pages/EmailStudio'
import Outbox from './pages/Outbox'
import Settings from './pages/Settings'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import axios from 'axios'

const queryClient = new QueryClient()

function LoadingScreen() {
    return (
        <div className="fixed inset-0 bg-zinc-950 flex items-center justify-center">
            <div className="text-center space-y-4">
                <div className="w-8 h-8 border-2 border-white/20 border-t-white rounded-full animate-spin mx-auto" />
                <p className="text-zinc-500 text-sm">Loading BruceLeads...</p>
            </div>
        </div>
    )
}

export default function App() {
    const [setupChecked, setSetupChecked] = useState(false)
    const [needsSetup, setNeedsSetup] = useState(false)

    useEffect(() => {
        axios.get('/api/setup/status')
            .then(res => {
                setNeedsSetup(!res.data.setup_complete)
                setSetupChecked(true)
            })
            .catch(() => setSetupChecked(true))
    }, [])

    if (!setupChecked) return <LoadingScreen />

    if (needsSetup) {
        return (
            <QueryClientProvider client={queryClient}>
                <SetupWizard onComplete={() => setNeedsSetup(false)} />
            </QueryClientProvider>
        )
    }

    return (
        <ErrorBoundary>
            <QueryClientProvider client={queryClient}>
                <UpdateBanner />
                <Router>
                    <Layout>
                        <Routes>
                            <Route path="/" element={<Dashboard />} />
                            <Route path="/find" element={<FindLeads />} />
                            <Route path="/manage" element={<ManageLeads />} />
                            <Route path="/email" element={<EmailStudio />} />
                            <Route path="/outbox" element={<Outbox />} />
                            <Route path="/settings" element={<Settings />} />
                        </Routes>
                    </Layout>
                </Router>
            </QueryClientProvider>
        </ErrorBoundary>
    )
}
