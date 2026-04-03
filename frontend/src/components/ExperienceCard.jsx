import '../styles/Cards.css'

export default function ExperienceCard({ entry }) {
  const dateRange = [
    entry.start_date || '',
    entry.is_current ? 'Present' : entry.end_date || '',
  ]
    .filter(Boolean)
    .join(' – ')

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">
          {entry.title} <span className="card-at">at</span> {entry.company}
        </span>
        {dateRange && <span className="card-meta">{dateRange}</span>}
      </div>
      {entry.location && <div className="card-subtitle">{entry.location}</div>}
      {entry.is_current && <span className="badge-current">Current</span>}
      {entry.description && <p className="card-description">{entry.description}</p>}
    </div>
  )
}
