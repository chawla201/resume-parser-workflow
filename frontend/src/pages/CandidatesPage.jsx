import { useEffect, useState } from 'react'
import CandidateListTable from '../components/CandidateListTable.jsx'
import CandidateDetail from '../components/CandidateDetail.jsx'
import Pagination from '../components/Pagination.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import { getCandidates, getCandidate } from '../api/client.js'
import '../styles/CandidatesPage.css'

const LIMIT = 20

export default function CandidatesPage() {
  const [status, setStatus] = useState('idle')
  const [candidates, setCandidates] = useState([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [error, setError] = useState(null)

  const [selectedId, setSelectedId] = useState(null)
  const [selectedCandidate, setSelectedCandidate] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState(null)

  useEffect(() => {
    fetchCandidates()
  }, [offset])

  async function fetchCandidates() {
    setStatus('loading')
    setError(null)
    try {
      const data = await getCandidates(LIMIT, offset)
      setCandidates(data.items)
      setTotal(data.total)
      setStatus('success')
    } catch (err) {
      setError(err.message)
      setStatus('error')
    }
  }

  async function handleRowClick(id) {
    if (selectedId === id) {
      setSelectedId(null)
      setSelectedCandidate(null)
      return
    }
    setSelectedId(id)
    setSelectedCandidate(null)
    setDetailError(null)
    setDetailLoading(true)
    try {
      const data = await getCandidate(id)
      setSelectedCandidate(data)
    } catch (err) {
      setDetailError(err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  function handlePageChange(newOffset) {
    setOffset(newOffset)
    setSelectedId(null)
    setSelectedCandidate(null)
  }

  return (
    <div className="candidates-page">
      <div className="candidates-header">
        <h1>All Candidates</h1>
        <p className="candidates-subtitle">
          {total > 0 ? `${total} candidate${total !== 1 ? 's' : ''} parsed so far` : 'No candidates yet'}
        </p>
      </div>

      {status === 'loading' && <LoadingSpinner message="Loading candidates…" />}

      {status === 'error' && (
        <ErrorBanner message={error} onDismiss={() => { setStatus('idle'); fetchCandidates() }} />
      )}

      {status === 'success' && (
        <>
          <CandidateListTable
            candidates={candidates}
            onRowClick={handleRowClick}
            selectedId={selectedId}
          />
          <Pagination
            total={total}
            limit={LIMIT}
            offset={offset}
            onPageChange={handlePageChange}
          />
        </>
      )}

      {selectedId && (
        <div className="candidates-detail">
          {detailLoading && <LoadingSpinner message="Loading details…" />}
          {detailError && <ErrorBanner message={detailError} />}
          {selectedCandidate && <CandidateDetail candidate={selectedCandidate} />}
        </div>
      )}
    </div>
  )
}
