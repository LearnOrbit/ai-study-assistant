import React, { useEffect, useState } from 'react'
import { documentAPI, summarizationAPI } from '../services/api'
import { request } from '../services/http'

const toDocument = doc => ({
  id: doc.id, name: doc.title, size: `${(doc.file_size / 1024).toFixed(1)} KB`,
  type: doc.document_type, status: doc.processing_status,
  uploadDate: new Date(doc.created_at).toLocaleDateString(),
})
const Library = () => {
  const [documents, setDocuments] = useState([])
  const [dragActive, setDragActive] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [error, setError] = useState('')
  const [summaryModal, setSummaryModal] = useState(null)
  const [searchModal, setSearchModal] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let active = true
    documentAPI.getDocuments().then(data => { if (active) setDocuments(data.map(toDocument)) })
      .catch(error => { if (active) setError(error.message) })
      .finally(() => { if (active) setInitialLoading(false) })
    return () => { active = false }
  }, [])
  const handleDrag = event => {
    event.preventDefault()
    event.stopPropagation()
    setDragActive(event.type !== 'dragleave')
  }
  const handleDrop = event => {
    event.preventDefault()
    setDragActive(false)
    handleFiles(Array.from(event.dataTransfer.files))
  }
  const handleFileSelect = event => {
    handleFiles(Array.from(event.target.files))
    event.target.value = ''
  }
  const handleFiles = async files => {
    if (isLoading || initialLoading) return
    setIsLoading(true)
    setError('')
    const failures = []
    for (const file of files) {
      try {
        if (!/\.(pdf|docx|txt)$/i.test(file.name)) throw new Error('Choose a PDF, DOCX, or TXT file.')
        if (!file.size || file.size > 10 * 1024 * 1024) throw new Error('Files must be nonempty and at most 10 MB.')
        const doc = await documentAPI.uploadDocument(file)
        setDocuments(previous => [toDocument(doc), ...previous])
        if (doc.processing_status === 'failed') failures.push(`${file.name}: ${doc.processing_error || 'Text extraction failed.'}`)
      } catch (error) { failures.push(`${file.name}: ${error.message}`) }
    }
    setError(failures.join(' '))
    setIsLoading(false)
  }
  const removeDocument = async id => {
    setIsLoading(true)
    setError('')
    try {
      await documentAPI.deleteDocument(id)
      setDocuments(previous => previous.filter(doc => doc.id !== id))
    } catch (error) { setError(error.message) }
    finally { setIsLoading(false) }
  }
  const getFileIcon = type => type === 'txt' ? '📝' : '📄'
  const handleSummarize = async doc => {
    setIsLoading(true)
    setSummaryModal({ loading: true })
    try {
      const data = await summarizationAPI.summarizeDocument(doc.id)
      setSummaryModal({ content: data.summary })
      setDocuments(previous => previous.map(item => item.id === doc.id ? { ...item, summary: data.summary } : item))
    } catch (error) { setSummaryModal({ error: error.message }) }
    finally { setIsLoading(false) }
  }
  const handleSearch = async doc => {
    if (!doc || !searchQuery.trim()) return
    setIsLoading(true)
    setSearchModal({ docId: doc.id, loading: true })
    try {
      const data = await request(`/documents/${doc.id}/search?q=${encodeURIComponent(searchQuery.trim())}`)
      setSearchModal({ docId: doc.id, results: data.results, searched: true })
    } catch (error) { setSearchModal({ docId: doc.id, error: error.message }) }
    finally { setIsLoading(false) }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">Document Library</h1>
        <p className="text-gray-600">Upload and manage your study materials</p>
      </div>

      {error && <p role="alert" className="mb-4 rounded-lg bg-red-50 text-red-700 p-4">{error}</p>}
      {(isLoading || initialLoading) && <p role="status" className="mb-4 text-gray-600">{initialLoading ? 'Loading your library…' : 'Working…'}</p>}
      {/* Upload Area */}
      <div className="bg-white rounded-xl shadow-lg p-8 mb-8">
        <div
          className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-blue-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="text-6xl mb-4">📁</div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">
            Drag & Drop your files here
          </h3>
          <p className="text-gray-500 mb-6">
            or click to browse (PDF, DOCX, TXT files supported)
          </p>

          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt"
            disabled={isLoading || initialLoading}
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />

          <label
            htmlFor="file-upload"
            className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 cursor-pointer inline-block transition-colors"
          >
            Choose Files
          </label>
        </div>
      </div>

      {/* Documents Grid */}
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-800">
            Your Documents ({documents.length})
          </h2>

        </div>

        {documents.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📂</div>
            <p className="text-gray-500 text-lg">No documents uploaded yet</p>
            <p className="text-gray-400">Upload your first document to get started!</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map(doc => (
              <div key={doc.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="text-2xl">{getFileIcon(doc.type)}</div>
                  <button
                    disabled={isLoading}
                    aria-label={`Delete ${doc.name}`}
                    onClick={() => removeDocument(doc.id)}
                    className="text-red-500 hover:text-red-700 text-sm"
                  >
                    ✕
                  </button>
                </div>

                <h3 className="font-medium text-gray-800 mb-2 truncate" title={doc.name}>
                  {doc.name}
                </h3>

                <div className="text-sm text-gray-500 space-y-1">
                  <p>Size: {doc.size}</p>
                  <p>Uploaded: {doc.uploadDate}</p>
                  <p>Status: {doc.status}</p>
                </div>

                {doc.summary && (
                  <div className="mt-3 p-2 bg-blue-50 rounded text-xs text-gray-700">
                    <strong>Summary:</strong> {doc.summary.substring(0, 100)}...
                  </div>
                )}

                <div className="mt-4 flex space-x-2">
                  <button
                    onClick={() => handleSummarize(doc)}
                    disabled={isLoading || doc.status !== 'completed'}
                    className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {isLoading ? '⏳' : '📊'} Summarize
                  </button>
                  <button
                    disabled={isLoading || doc.status !== 'completed'}
                    onClick={() => { setSearchQuery(''); setSearchModal({ docId: doc.id }) }}
                    className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200"
                  >
                    🔍 Search
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Summary Modal */}
      {summaryModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-96 overflow-y-auto p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-800">Document Summary</h2>
              <button
                onClick={() => setSummaryModal(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ✕
              </button>
            </div>

            {summaryModal.loading ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-2">⏳</div>
                <p className="text-gray-600">Generating summary...</p>
              </div>
            ) : summaryModal.error ? (
              <div className="bg-red-50 p-4 rounded text-red-700">
                <strong>Error:</strong> {summaryModal.error}
              </div>
            ) : (
              <div className="text-gray-700 whitespace-pre-wrap">
                {summaryModal.content}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Search Modal */}
      {searchModal && searchModal.docId !== undefined && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold text-gray-800">Search Document</h2>
              <button
                onClick={() => setSearchModal(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ✕
              </button>
            </div>

            <div className="mb-4 flex space-x-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter search query..."
                aria-label="Search document text"
                className="min-w-0 flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={() => handleSearch(documents.find(d => d.id === searchModal.docId))}
                disabled={isLoading || !searchQuery.trim()}
                className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 disabled:bg-gray-300"
              >
                {isLoading ? '🔄' : '🔍'} Search
              </button>
            </div>

            {searchModal.loading ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-2">🔍</div>
                <p className="text-gray-600">Searching...</p>
              </div>
            ) : searchModal.error ? (
              <div className="bg-red-50 p-4 rounded text-red-700">
                <strong>Error:</strong> {searchModal.error}
              </div>
            ) : searchModal.results && searchModal.results.length > 0 ? (
              <div className="space-y-4">
                {searchModal.results.map((result, index) => (
                  <div key={index} className="border-l-4 border-green-500 pl-4 py-2">
                    <h3 className="font-semibold text-gray-800">{result.title}</h3>
                    <p className="text-sm text-gray-600">{result.excerpt}</p>
                    <p className="text-xs text-green-600 mt-1">✓ {result.relevance}</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-center py-4">{searchModal.searched ? 'No matching text found.' : 'Enter a search query and click Search'}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Library