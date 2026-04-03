import { useState } from 'react'
import CandidateTable from './CandidateTable.jsx'
import JsonView from './JsonView.jsx'
import '../styles/CandidateDetail.css'

export default function CandidateDetail({ candidate }) {
  const [activeTab, setActiveTab] = useState('table')

  return (
    <div className="candidate-detail">
      <div className="tab-bar">
        <button
          className={`tab-btn${activeTab === 'table' ? ' active' : ''}`}
          onClick={() => setActiveTab('table')}
        >
          Structured View
        </button>
        <button
          className={`tab-btn${activeTab === 'json' ? ' active' : ''}`}
          onClick={() => setActiveTab('json')}
        >
          Raw JSON
        </button>
      </div>
      <div className="tab-content">
        {activeTab === 'table' ? (
          <CandidateTable candidate={candidate} />
        ) : (
          <JsonView data={candidate} />
        )}
      </div>
    </div>
  )
}
