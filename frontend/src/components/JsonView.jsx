import '../styles/JsonView.css'

export default function JsonView({ data }) {
  return (
    <pre className="json-view">
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  )
}
