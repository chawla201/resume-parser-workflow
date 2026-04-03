import { useState } from 'react'
import DropZone from '../components/DropZone.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import CandidateDetail from '../components/CandidateDetail.jsx'
import { parseResume } from '../api/client.js'
import '../styles/UploadPage.css'

export default function UploadPage() {
  const [status, setStatus] = useState('idle')
  const [candidate, setCandidate] = useState(null)
  const [error, setError] = useState(null)

  async function handleFileSelected(file) {
    setStatus('loading')
    setError(null)
    setCandidate(null)
    try {
      const result = await parseResume(file)
      setCandidate(result.candidate)
      setStatus('success')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  return (
    <div className="upload-page">
      <div className="upload-header">
        <h1>Parse a Resume</h1>
        <p className="upload-subtitle">
          Upload a PDF, DOCX, or TXT file and extract structured candidate data using a local Ollama model.
        </p>
      </div>

      <DropZone onFileSelected={handleFileSelected} disabled={status === 'loading'} />

      {status === 'loading' && (
        <LoadingSpinner message="Parsing with Ollama… this may take up to 30 seconds" />
      )}

      {status === 'error' && (
        <ErrorBanner message={error} onDismiss={() => setStatus('idle')} />
      )}

      {status === 'success' && candidate && (
        <div className="upload-result">
          <CandidateDetail candidate={candidate} />
        </div>
      )}
    </div>
  )
}
