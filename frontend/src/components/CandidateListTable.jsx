import '../styles/CandidateListTable.css'

function formatDate(iso) {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(iso))
}

function truncateSkills(skills) {
  if (!skills || skills.length === 0) return '—'
  const shown = skills.slice(0, 3)
  const rest = skills.length - 3
  return rest > 0 ? `${shown.join(', ')} +${rest} more` : shown.join(', ')
}

export default function CandidateListTable({ candidates, onRowClick, selectedId }) {
  if (candidates.length === 0) {
    return <p className="clt-empty">No candidates found.</p>
  }

  return (
    <div className="clt-wrapper">
      <table className="clt-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Location</th>
            <th>Skills</th>
            <th>Parsed</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c) => (
            <tr
              key={c.id}
              className={`clt-row${selectedId === c.id ? ' selected' : ''}`}
              onClick={() => onRowClick(c.id)}
            >
              <td className="clt-name">{c.full_name}</td>
              <td>{c.email || '—'}</td>
              <td>{c.location || '—'}</td>
              <td className="clt-skills">{truncateSkills(c.skills)}</td>
              <td>{formatDate(c.parsed_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
