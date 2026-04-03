import '../styles/LoadingSpinner.css'

export default function LoadingSpinner({ message = 'Loading…' }) {
  return (
    <div className="spinner-wrapper">
      <div className="spinner" />
      <p className="spinner-message">{message}</p>
    </div>
  )
}
