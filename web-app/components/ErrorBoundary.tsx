import React from 'react';
import { toast } from 'react-toastify';

type State = { hasError: boolean; error?: Error };

export default class ErrorBoundary extends React.Component<React.PropsWithChildren<{}>, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    // Log to console or any logging infra
    console.error('ErrorBoundary caught error', error, errorInfo);
    toast.error(error.message || 'Something went wrong');
  }

  render(): React.ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-6">
          <div className="text-center">
            <h1 className="text-2xl font-semibold mb-2">Something went wrong</h1>
            <p className="text-sm text-muted-foreground">Please refresh the page or try again.</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
