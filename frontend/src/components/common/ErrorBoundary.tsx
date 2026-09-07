import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { Button } from "../primitives/Button";

interface Props {
  children: ReactNode;
  locationKey?: string;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an uncaught exception:", error, errorInfo);
  }

  public componentDidUpdate(prevProps: Props) {
    // Automatically recover when user navigates to another route
    if (this.state.hasError && prevProps.locationKey !== this.props.locationKey) {
      this.setState({ hasError: false, error: null });
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            padding: "var(--space-8, 32px)",
            maxWidth: "760px",
            margin: "40px auto",
            background: "var(--surface-1, #12151b)",
            border: "1px solid var(--line-strong, rgba(255,255,255,0.12))",
            borderRadius: "var(--radius-card, 8px)",
            boxShadow: "0 16px 36px rgba(0,0,0,0.5)",
          }}
        >
          <div
            style={{
              font: "var(--type-mono-xs, 11px monospace)",
              color: "var(--signal-amber, #f59e0b)",
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              marginBottom: "8px",
            }}
          >
            System Diagnostics · Safe Recovery Mode
          </div>
          <h2
            style={{
              fontSize: "20px",
              fontFamily: "var(--font-sans, sans-serif)",
              fontWeight: 600,
              color: "var(--text-primary, #ffffff)",
              marginBottom: "12px",
            }}
          >
            {this.props.fallbackTitle || "Investigation View Interrupted"}
          </h2>
          <p
            style={{
              font: "var(--type-body, 14px sans-serif)",
              color: "var(--text-secondary, #94a3b8)",
              marginBottom: "20px",
              lineHeight: 1.6,
            }}
          >
            A component encountered an unexpected exception during render or data transition.
            The surrounding shell and telemetry channels remain active.
          </p>

          {this.state.error && (
            <div
              style={{
                background: "rgba(0, 0, 0, 0.4)",
                padding: "12px 14px",
                borderRadius: "6px",
                border: "1px solid rgba(245, 158, 11, 0.2)",
                font: "12px/1.5 monospace",
                color: "#fca5a5",
                marginBottom: "24px",
                overflowX: "auto",
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
              }}
            >
              {this.state.error.message || String(this.state.error)}
            </div>
          )}

          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Button variant="primary" onClick={this.handleReset}>
              Retry View
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                window.location.href = "/investigations";
              }}
            >
              All Investigations
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                window.location.href = "/command";
              }}
            >
              Command Center
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
