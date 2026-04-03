import { Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar.jsx'
import UploadPage from './pages/UploadPage.jsx'
import CandidatesPage from './pages/CandidatesPage.jsx'

export default function App() {
  return (
    <div className="app">
      <NavBar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
        </Routes>
      </main>
    </div>
  )
}
