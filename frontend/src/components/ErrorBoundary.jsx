import { Component } from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
    constructor(props) {
        super(props)
        this.state = { hasError: false, error: null }
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error }
    }

    componentDidCatch(error, info) {
        console.error('[BruceLeads] UI Error:', error, info?.componentStack)
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="fixed inset-0 bg-zinc-950 flex items-center justify-center p-4">
                    <div className="max-w-md text-center space-y-6">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20">
                            <AlertCircle size={32} className="text-red-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Something went wrong</h2>
                            <p className="text-zinc-400 mt-2 text-sm">
                                An unexpected error occurred. Please reload the app.
                            </p>
                        </div>
                        <button
                            onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/' }}
                            className="px-6 py-3 bg-white text-black font-semibold rounded-xl hover:bg-zinc-200 transition-colors inline-flex items-center gap-2"
                        >
                            <RefreshCw size={16} /> Reload App
                        </button>
                    </div>
                </div>
            )
        }
        return this.props.children
    }
}
