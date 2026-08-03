"use client";

import Link from "next/link";
import { Component, type ErrorInfo, type ReactNode } from "react";

type CommercialErrorBoundaryProps = {
  children: ReactNode;
  fallbackTitle: string;
  fallbackMessage: string;
  retryLabel: string;
  homeLabel: string;
  homeHref?: string;
  correlationId?: string | null;
};

type CommercialErrorBoundaryState = {
  hasError: boolean;
};

/**
 * Prevents unhandled render errors from leaking stack traces or internal messages.
 */
export class CommercialErrorBoundary extends Component<
  CommercialErrorBoundaryProps,
  CommercialErrorBoundaryState
> {
  state: CommercialErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): CommercialErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    if (process.env.NODE_ENV !== "production") {
      console.error("[CommercialErrorBoundary]", error, info.componentStack);
    }
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="mx-auto max-w-lg space-y-3 rounded-xl border p-6"
          style={{ borderColor: "var(--ms-border-default)" }}
          data-testid="commercial-error-boundary"
        >
          <p className="text-sm font-semibold">{this.props.fallbackTitle}</p>
          <p className="text-sm" style={{ color: "var(--ms-text-secondary)" }}>
            {this.props.fallbackMessage}
          </p>
          {process.env.NODE_ENV !== "production" && this.props.correlationId ? (
            <p className="text-xs font-mono" style={{ color: "var(--ms-text-muted)" }}>
              correlation_id: {this.props.correlationId}
            </p>
          ) : null}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-md px-4 py-2 text-sm font-semibold"
              style={{
                background: "var(--ms-brand-primary)",
                color: "var(--ms-text-on-brand, #fff)",
              }}
              onClick={this.handleRetry}
              data-testid="commercial-error-boundary-retry"
            >
              {this.props.retryLabel}
            </button>
            <Link
              href={this.props.homeHref ?? "/workspace"}
              className="rounded-md border px-4 py-2 text-sm font-semibold"
              style={{ borderColor: "var(--ms-border-default)" }}
              data-testid="commercial-error-boundary-home"
            >
              {this.props.homeLabel}
            </Link>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
