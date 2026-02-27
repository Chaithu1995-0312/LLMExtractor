// ============================================================
//  ErrorBoundary — Global React Error Boundary
//  Catches runtime errors in any child component tree and
//  renders a styled fallback instead of a white screen.
//  Usage: Wrap <AppLayout> in App.tsx with <ErrorBoundary>
// ============================================================

import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });
    // Surface to console for debugging — replace with Sentry/telemetry as needed
    console.error('[ErrorBoundary] Uncaught component error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    const { error, errorInfo } = this.state;
    const componentStack = errorInfo?.componentStack ?? '';

    return (
      <div
        style={{
          minHeight: '100vh',
          background: '#030609',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '32px',
          fontFamily: 'monospace',
        }}
      >
        {/* Icon */}
        <div style={{ marginBottom: '24px' }}>
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="1.5">
            <path strokeLinecap="round" strokeLinejoin="round"
              d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
          </svg>
        </div>

        {/* Title */}
        <h1
          style={{
            fontSize: '13px',
            fontWeight: 900,
            letterSpacing: '0.4em',
            textTransform: 'uppercase',
            color: '#f87171',
            marginBottom: '8px',
            textShadow: '0 0 20px rgba(248,113,113,0.4)',
          }}
        >
          SUBSYSTEM FAULT DETECTED
        </h1>
        <p
          style={{
            fontSize: '10px',
            letterSpacing: '0.2em',
            color: 'rgba(255,255,255,0.3)',
            textTransform: 'uppercase',
            marginBottom: '32px',
          }}
        >
          A component encountered an unrecoverable error
        </p>

        {/* Error message */}
        <div
          style={{
            width: '100%',
            maxWidth: '640px',
            background: 'rgba(248,113,113,0.05)',
            border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px',
          }}
        >
          <div style={{ fontSize: '9px', color: 'rgba(255,255,255,0.3)', letterSpacing: '0.2em', marginBottom: '6px' }}>
            ERROR MESSAGE
          </div>
          <div style={{ fontSize: '11px', color: '#f87171', wordBreak: 'break-all' }}>
            {error?.message ?? 'Unknown error'}
          </div>
        </div>

        {/* Stack trace (collapsible) */}
        {componentStack && (
          <details
            style={{
              width: '100%',
              maxWidth: '640px',
              marginBottom: '24px',
            }}
          >
            <summary
              style={{
                fontSize: '9px',
                color: 'rgba(255,255,255,0.3)',
                letterSpacing: '0.2em',
                textTransform: 'uppercase',
                cursor: 'pointer',
                padding: '8px 0',
              }}
            >
              Component Stack (click to expand)
            </summary>
            <pre
              style={{
                fontSize: '9px',
                color: 'rgba(255,255,255,0.4)',
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '6px',
                padding: '12px',
                overflow: 'auto',
                maxHeight: '200px',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-all',
              }}
            >
              {componentStack}
            </pre>
          </details>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={this.handleReset}
            style={{
              padding: '10px 24px',
              background: 'rgba(34,211,238,0.08)',
              border: '1px solid rgba(34,211,238,0.3)',
              borderRadius: '6px',
              color: '#22d3ee',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              cursor: 'pointer',
            }}
          >
            ↺ Retry Component
          </button>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 24px',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: '6px',
              color: 'rgba(255,255,255,0.5)',
              fontSize: '10px',
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              cursor: 'pointer',
            }}
          >
            ⟳ Full Reload
          </button>
        </div>

        {/* Build hint */}
        <p
          style={{
            marginTop: '32px',
            fontSize: '8px',
            color: 'rgba(255,255,255,0.15)',
            letterSpacing: '0.1em',
          }}
        >
          NEXUS JARVIS · ERROR BOUNDARY ACTIVE · CHECK CONSOLE FOR FULL TRACE
        </p>
      </div>
    );
  }
}
