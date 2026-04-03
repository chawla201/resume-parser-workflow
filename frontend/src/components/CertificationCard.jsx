import '../styles/Cards.css'

export default function CertificationCard({ entry }) {
  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">{entry.name}</span>
        {entry.year && <span className="card-meta">{entry.year}</span>}
      </div>
      {entry.issuer && <div className="card-subtitle">{entry.issuer}</div>}
    </div>
  )
}
