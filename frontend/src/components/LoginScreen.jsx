import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Zap, Upload, Loader2, AlertCircle } from 'lucide-react'
import axios from 'axios'

export default function LoginScreen({ onLogin }) {
    const [hasCreds, setHasCreds] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const fileRef = useRef(null)

    useEffect(() => {
        axios.get('/api/auth/has-credentials')
            .then(r => setHasCreds(r.data.exists))
            .catch(() => setHasCreds(false))
    }, [])

    const handleUpload = async (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        setLoading(true); setError('')
        try {
            const fd = new FormData()
            fd.append('file', file)
            await axios.post('/api/setup/gmail-upload', fd, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            setHasCreds(true)
        } catch (err) {
            setError(err.response?.data?.detail || 'Invalid credentials file')
        }
        setLoading(false)
    }

    const handleLogin = async () => {
        setLoading(true); setError('')
        try {
            const res = await axios.get('/api/auth/login-url', {
                params: { redirect: window.location.origin },
            })
            window.location.href = res.data.url
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to start login')
            setLoading(false)
        }
    }

    return (
        <div className="fixed inset-0 bg-zinc-950 flex items-center justify-center p-4">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md text-center space-y-8">

                {/* Logo */}
                <div className="space-y-3">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-white/5 border border-zinc-800">
                        <Zap size={36} className="text-white" />
                    </div>
                    <h1 className="text-3xl font-bold tracking-tight text-white">BruceLeads</h1>
                    <p className="text-zinc-500 text-sm">Sign in with your Google account to get started</p>
                </div>

                {/* Body */}
                {hasCreds === null ? (
                    <Loader2 size={24} className="animate-spin mx-auto text-zinc-500" />
                ) : hasCreds ? (
                    <button onClick={handleLogin} disabled={loading}
                        className="w-full flex items-center justify-center gap-3 px-6 py-3.5 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors disabled:opacity-50">
                        {loading ? <Loader2 size={20} className="animate-spin" /> : (
                            <svg width="20" height="20" viewBox="0 0 24 24">
                                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" />
                                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                            </svg>
                        )}
                        Sign in with Google
                    </button>
                ) : (
                    <div className="space-y-4">
                        <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 text-left space-y-3">
                            <h3 className="font-semibold text-white text-sm">Setup Required</h3>
                            <p className="text-xs text-zinc-400 leading-relaxed">
                                Upload your Google Cloud OAuth credentials JSON to enable sign-in.
                                This is a one-time setup.
                            </p>
                            <ol className="text-xs text-zinc-500 space-y-1 list-decimal list-inside">
                                <li>Go to <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Google Cloud Console</a></li>
                                <li>Create an OAuth 2.0 Client ID (Desktop app)</li>
                                <li>Download the JSON and upload below</li>
                            </ol>
                        </div>
                        <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleUpload} />
                        <button onClick={() => fileRef.current?.click()} disabled={loading}
                            className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-zinc-800 border border-zinc-700 text-white font-semibold rounded-xl hover:bg-zinc-700 transition-colors disabled:opacity-50">
                            {loading ? <Loader2 size={18} className="animate-spin" /> : <Upload size={18} />}
                            Upload credentials.json
                        </button>
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="flex items-center gap-2 px-4 py-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg text-sm">
                        <AlertCircle size={16} /> {error}
                    </div>
                )}
            </motion.div>
        </div>
    )
}
