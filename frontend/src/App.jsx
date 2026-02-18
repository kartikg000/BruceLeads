
import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import SetupWizard from './components/SetupWizard'
import LoginScreen from './components/LoginScreen'
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
    const [authChecked, setAuthChecked] = useState(false)
    const [isLoggedIn, setIsLoggedIn] = useState(false)
    const [user, setUser] = useState(null)
    const [setupChecked, setSetupChecked] = useState(false)
    const [needsSetup, setNeedsSetup] = useState(false)

    const checkAuth = () => {
        const token = localStorage.getItem('bruce_token') || ''
        axios.get('/api/auth/me', { params: { token } })
            .then(res => {
                setIsLoggedIn(res.data.authenticated)
                if (res.data.authenticated) setUser(res.data.user)
                setAuthChecked(true)
            })
            .catch(() => setAuthChecked(true))
    }

    useEffect(() => {
        // Handle OAuth callback token in URL
        const params = new URLSearchParams(window.location.search)
        const authToken = params.get('auth_token')
        const authError = params.get('auth_error')
        if (authToken) {
            localStorage.setItem('bruce_token', authToken)
            window.history.replaceState({}, '', '/')
        }
        if (authError) {
            console.error('Auth error:', authError)
            window.history.replaceState({}, '', '/')
        }
        checkAuth()
    }, [])

    // Check setup status after login
    useEffect(() => {
        if (isLoggedIn && !setupChecked) {
            axios.get('/api/setup/status')
                .then(res => {
                    setNeedsSetup(!res.data.setup_complete)
                    setSetupChecked(true)
                })
                .catch(() => setSetupChecked(true))
        }
    }, [isLoggedIn])

    const handleLogout = async () => {
        await axios.post('/api/auth/logout').catch(() => { })
        localStorage.removeItem('bruce_token')
        setIsLoggedIn(false)
        setUser(null)
        setSetupChecked(false)
    }

    if (!authChecked) return <LoadingScreen />
    if (!isLoggedIn) return <LoginScreen onLogin={() => checkAuth()} />
    if (!setupChecked) return <LoadingScreen />

    if (needsSetup) {
        return (
            <QueryClientProvider client={queryClient}>
                <SetupWizard onComplete={() => setNeedsSetup(false)} />
            </QueryClientProvider>
        )
    }

    return (
        <QueryClientProvider client={queryClient}>
            <Router>
                <Layout user={user} onLogout={handleLogout}>
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
    )
}
