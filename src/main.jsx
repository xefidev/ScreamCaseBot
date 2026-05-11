import React from 'react'
import ReactDOM from 'react-dom/client'
import { TonConnectUIProvider } from '@tonconnect/ui-react'
import App from './App'
import './index.css'

// Initialize Telegram WebApp if available
if (window.Telegram?.WebApp) {
  const tg = window.Telegram.WebApp
  tg.ready()
  tg.expand()
  tg.enableClosingConfirmation()
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <TonConnectUIProvider manifestUrl="https://scream-case-bot.vercel.app/tonconnect-manifest.json">
      <App />
    </TonConnectUIProvider>
  </React.StrictMode>,
)
