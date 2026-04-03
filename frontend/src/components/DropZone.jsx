import { useRef, useState } from 'react'
import '../styles/DropZone.css'

const ALLOWED = ['.pdf', '.docx', '.txt']

function getExtension(file) {
  return '.' + file.name.split('.').pop().toLowerCase()
}

export default function DropZone({ onFileSelected, disabled }) {
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileError, setFileError] = useState(null)
  const inputRef = useRef(null)

  function handleFile(file) {
    if (!file) return
    if (!ALLOWED.includes(getExtension(file))) {
      setFileError(`Unsupported file type. Allowed: ${ALLOWED.join(', ')}`)
      return
    }
    setFileError(null)
    setSelectedFile(file)
    onFileSelected(file)
  }

  function onDragOver(e) {
    e.preventDefault()
    if (!disabled) setIsDragging(true)
  }

  function onDragLeave() {
    setIsDragging(false)
  }

  function onDrop(e) {
    e.preventDefault()
    setIsDragging(false)
    if (!disabled) handleFile(e.dataTransfer.files[0])
  }

  function onClick() {
    if (!disabled) inputRef.current?.click()
  }

  function onChange(e) {
    handleFile(e.target.files[0])
    // reset so the same file can be re-selected
    e.target.value = ''
  }

  return (
    <div
      className={`dropzone${isDragging ? ' dragging' : ''}${disabled ? ' disabled' : ''}`}
      onDragOver={onDragOver}
      onDragEnter={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={onClick}
      role="button"
      tabIndex={disabled ? -1 : 0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label="Upload resume file"
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={onChange}
        className="dropzone-input"
        tabIndex={-1}
      />
      <div className="dropzone-icon">📄</div>
      <p className="dropzone-text">
        {selectedFile
          ? selectedFile.name
          : 'Drag & drop a resume here, or click to select'}
      </p>
      <p className="dropzone-hint">Supports PDF, DOCX, TXT</p>
      {fileError && <p className="dropzone-error">{fileError}</p>}
    </div>
  )
}
