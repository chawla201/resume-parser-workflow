import '../styles/Pagination.css'

export default function Pagination({ total, limit, offset, onPageChange }) {
  const start = offset + 1
  const end = Math.min(offset + limit, total)
  const hasPrev = offset > 0
  const hasNext = offset + limit < total

  return (
    <div className="pagination">
      <span className="pagination-info">
        {total === 0 ? 'No candidates' : `Showing ${start}–${end} of ${total}`}
      </span>
      <div className="pagination-controls">
        <button
          className="page-btn"
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={!hasPrev}
        >
          ← Prev
        </button>
        <button
          className="page-btn"
          onClick={() => onPageChange(offset + limit)}
          disabled={!hasNext}
        >
          Next →
        </button>
      </div>
    </div>
  )
}
