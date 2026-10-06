import React from "react"
import { AlertTriangle } from "lucide-react"

interface Props {
  children: React.ReactNode
}

interface State {
  error: Error | null
}

/** Keeps one broken page from blanking the whole application. Give it a `key` (e.g. the route)
 * so navigating elsewhere starts with a fresh boundary. */
export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error("Page crashed:", error, info.componentStack)
  }

  render(): React.ReactNode {
    if (!this.state.error) return this.props.children
    return (
      <div className="card empty-state" role="alert">
        <AlertTriangle size={40} className="empty-state-icon" aria-hidden="true" />
        <h2 className="card-title">This page ran into a problem</h2>
        <p className="muted">{this.state.error.message}</p>
        <button type="button" className="btn btn-outline" style={{ marginTop: 16 }} onClick={() => this.setState({ error: null })}>
          Try again
        </button>
      </div>
    )
  }
}
export default ErrorBoundary
