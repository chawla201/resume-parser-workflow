import '../styles/Cards.css'

export default function EducationCard({ entry }) {
  const years =
    entry.start_year && entry.end_year
      ? `${entry.start_year} – ${entry.end_year}`
      : entry.start_year || entry.end_year || null

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{entry.institution}</span>
        {years && <span className="card-meta">{years}</span>}
      </div>
      {(entry.degree || entry.field_of_study) && (
        <div className="card-subtitle">
          {[entry.degree, entry.field_of_study].filter(Boolean).join(' · ')}
        </div>
      )}
    </div>
  )
}
