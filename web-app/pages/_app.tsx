import type { AppProps } from 'next/app';
import '@/styles/globals.css';
import { AuthContextProvider } from '@/providers/auth-provider';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import ErrorBoundary from '@/components/ErrorBoundary';
import Navbar from '@/components/Navbar';
import GlobalLoader from '@/components/GlobalLoader';

export default function MyApp({ Component, pageProps }: AppProps) {

  return (
    <ErrorBoundary>
      <AuthContextProvider>
        <ToastContainer position="top-right" autoClose={3000} />
        <Navbar />
        <GlobalLoader />
        <Component {...pageProps} />
      </AuthContextProvider>
    </ErrorBoundary>
  );
}
