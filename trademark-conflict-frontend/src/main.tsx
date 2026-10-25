import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { finishSignInCallback } from './services/auth'

async function bootstrap() {
  try {
    await finishSignInCallback();
    createRoot(document.getElementById('root')!).render(
      <StrictMode>
        <App />
      </StrictMode>,
    );
  } catch (error) {
    const root = document.getElementById('root');
    if (root) {
      root.textContent = error instanceof Error
        ? `Sign-in failed: ${error.message}`
        : 'Sign-in failed.';
    }
  }
}

void bootstrap();
