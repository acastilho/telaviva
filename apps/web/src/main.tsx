import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App'
import { LiveViewer } from './LiveViewer'
import './styles.css'
import './brand.css'
import './official-brand.css'
import './product.css'
import './system.css'
import './live-broadcast.css'

const liveRoomId = new URLSearchParams(window.location.search).get('live')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {liveRoomId ? <LiveViewer roomId={liveRoomId} /> : <App />}
  </StrictMode>,
)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => {
      // The app remains fully usable when offline support is unavailable.
    })
  })
}
