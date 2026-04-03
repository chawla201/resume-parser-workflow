import SkillTag from './SkillTag.jsx'
import EducationCard from './EducationCard.jsx'
import ExperienceCard from './ExperienceCard.jsx'
import CertificationCard from './CertificationCard.jsx'
import '../styles/CandidateTable.css'

function Section({ title, children }) {
  return (
    <div className="ct-section">
      <h3 className="ct-section-title">{title}</h3>
      {children}
    </div>
  )
}

export default function CandidateTable({ candidate }) {
  return (
    <div className="candidate-table">
      <div className="ct-header">
        <div className="ct-field-grid">
          <div className="ct-field">
            <span className="ct-label">Name</span>
            <span className="ct-value ct-name">{candidate.full_name}</span>
          </div>
          {candidate.email && (
            <div className="ct-field">
              <span className="ct-label">Email</span>
              <a className="ct-value ct-link" href={`mailto:${candidate.email}`}>
                {candidate.email}
              </a>
            </div>
          )}
          {candidate.phone && (
            <div className="ct-field">
              <span className="ct-label">Phone</span>
              <a className="ct-value ct-link" href={`tel:${candidate.phone}`}>
                {candidate.phone}
              </a>
            </div>
          )}
          {candidate.location && (
            <div className="ct-field">
              <span className="ct-label">Location</span>
              <span className="ct-value">{candidate.location}</span>
            </div>
          )}
          {candidate.linkedin_url && (
            <div className="ct-field">
              <span className="ct-label">LinkedIn</span>
              <a
                className="ct-value ct-link"
                href={
                  candidate.linkedin_url.startsWith('http')
                    ? candidate.linkedin_url
                    : `https://${candidate.linkedin_url}`
                }
                target="_blank"
                rel="noreferrer"
              >
                {candidate.linkedin_url}
              </a>
            </div>
          )}
          {candidate.github_url && (
            <div className="ct-field">
              <span className="ct-label">GitHub</span>
              <a
                className="ct-value ct-link"
                href={
                  candidate.github_url.startsWith('http')
                    ? candidate.github_url
                    : `https://${candidate.github_url}`
                }
                target="_blank"
                rel="noreferrer"
              >
                {candidate.github_url}
              </a>
            </div>
          )}
        </div>
      </div>

      {candidate.summary && (
        <Section title="Summary">
          <p className="ct-summary">{candidate.summary}</p>
        </Section>
      )}

      {candidate.skills?.length > 0 && (
        <Section title="Skills">
          <div className="ct-tags">
            {candidate.skills.map((s) => (
              <SkillTag key={s} label={s} />
            ))}
          </div>
        </Section>
      )}

      {candidate.languages?.length > 0 && (
        <Section title="Languages">
          <div className="ct-tags">
            {candidate.languages.map((l) => (
              <SkillTag key={l} label={l} />
            ))}
          </div>
        </Section>
      )}

      {candidate.education?.length > 0 && (
        <Section title="Education">
          {candidate.education.map((e, i) => (
            <EducationCard key={i} entry={e} />
          ))}
        </Section>
      )}

      {candidate.experience?.length > 0 && (
        <Section title="Experience">
          {candidate.experience.map((e, i) => (
            <ExperienceCard key={i} entry={e} />
          ))}
        </Section>
      )}

      {candidate.certifications?.length > 0 && (
        <Section title="Certifications">
          {candidate.certifications.map((c, i) => (
            <CertificationCard key={i} entry={c} />
          ))}
        </Section>
      )}
    </div>
  )
}
