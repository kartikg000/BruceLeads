import { useState, useEffect, useCallback } from 'react'
import { Download, X, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react'
import axios from 'axios'

/**
 * UpdateBanner — shown at the top of the app when a new version is available.
 * Checks /api/update/check on mount. If update_available, shows a banner with
 * version info + "Update Now" button that calls /api/update/apply.
 */
export default function UpdateBanner() {
    const [info, setInfo] = useState(null)        // { update_available, current_version, latest_version, release_notes }
    const [status, setStatus] = useState('idle')   // idle | checking | available | downloading | done | error
    const [dismissed, setDismissed] = useState(false)
    const [error, setError] = useState(null)

    // Check on mount
    useEffect(() => {
        setStatus('checking')
        axios.get('/api/update/check')
            .then(res => {
                setInfo(res.data)
                setStatus(res.data.update_available ? 'available' : 'idle')
            })
            .catch(() => setStatus('idle'))    // silently ignore — not critical
    }, [])

    const handleUpdate = useCallback(async () => {
        setStatus('downloading')
        setError(null)
        try {
            const res = await axios.post('/api/update/apply')
            if (res.data.status === 'already_up_to_date') {
                setStatus('idle')
                return
            }
            setStatus('done')
            // The server will shut down and restart. Poll until it's back (max 2 min).
            let attempts = 0
            const maxAttempts = 40  // 40 * 3s = 2 min
            const poll = setInterval(async () => {
                attempts++
                if (attempts > maxAttempts) {
                    clearInterval(poll)
                    setError('Server did not restart in time. Please restart the app manually.')
                    setStatus('error')
                    return
                }
                try {
                    await axios.get('/api/update/check')
                    clearInterval(poll)
                    window.location.reload()
                } catch { /* server still restarting */ }
            }, 3000)
        } catch (err) {
            const detail = err.response?.data?.detail
            // Don't expose raw server error details — show a generic message
            setError(typeof detail === 'string' && detail.length < 200
                ? detail
                : 'Update failed. Please try again or download manually from GitHub.')
            setStatus('error')
        }
    }, [])

    // Nothing to show
    if (status === 'idle' || status === 'checking' || dismissed) return null

    return (
        <div className={`
            w-full px-4 py-2.5 flex items-center justify-between gap-3 text-sm
            ${status === 'error' ? 'bg-red-500/10 border-b border-red-500/20 text-red-300'
                : status === 'done' ? 'bg-green-500/10 border-b border-green-500/20 text-green-300'
                    : 'bg-indigo-500/10 border-b border-indigo-500/20 text-indigo-300'}
        `}>
            {/* Left: icon + message */}
            <div className="flex items-center gap-2 min-w-0">
                {status === 'available' && (
                    <>
                        <Download className="w-4 h-4 shrink-0" />
                        <span>
                            <strong>BruceLeads v{info?.latest_version}</strong> is available
                            <span className="text-zinc-400 ml-1">(you have v{info?.current_version})</span>
                        </span>
                    </>
                )}
                {status === 'downloading' && (
                    <>
                        <RefreshCw className="w-4 h-4 shrink-0 animate-spin" />
                        <span>Downloading update… the app will restart automatically.</span>
                    </>
                )}
                {status === 'done' && (
                    <>
                        <CheckCircle className="w-4 h-4 shrink-0" />
                        <span>Update installed! The app is restarting — this page will reload shortly.</span>
                    </>
                )}
                {status === 'error' && (
                    <>
                        <AlertTriangle className="w-4 h-4 shrink-0" />
                        <span>{error}</span>
                    </>
                )}
            </div>

            {/* Right: actions */}
            <div className="flex items-center gap-2 shrink-0">
                {status === 'available' && (
                    <button
                        onClick={handleUpdate}
                        className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
                    >
                        Update Now
                    </button>
                )}
                {status === 'error' && (
                    <button
                        onClick={handleUpdate}
                        className="px-3 py-1 rounded bg-red-600 hover:bg-red-500 text-white text-xs font-medium transition-colors"
                    >
                        Retry
                    </button>
                )}
                {(status === 'available' || status === 'error') && (
                    <button onClick={() => setDismissed(true)} className="p-1 hover:bg-white/10 rounded transition-colors">
                        <X className="w-3.5 h-3.5" />
                    </button>
                )}
            </div>
        </div>
    )
}
