import React, { useState, useEffect, useRef } from 'react'
import { useSearchParams } from 'react-router-dom'
import { post, upload } from '../services/http'
import chatService from '../services/chatService'

const Study = () => {
  const [message, setMessage] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const allowedTabs = ['chat', 'summarize', 'image', 'audio', 'doubt']
  const activeTab = allowedTabs.includes(searchParams.get('tab')) ? searchParams.get('tab') : 'chat'
  const setActiveTab = tab => { setSearchParams({ tab }); setResults([]) }
  const recordingRef = useRef(null)
  useEffect(() => () => {
    const recorder = recordingRef.current
    if (recorder) {
      recorder.onstop = null
      if (recorder.state !== 'inactive') recorder.stop()
      recorder.stream.getTracks().forEach(track => track.stop())
    }
  }, [])
  const [summarizeInput, setSummarizeInput] = useState('')
  const [doubtInput, setDoubtInput] = useState('')
  const [audioRecording, setAudioRecording] = useState(false)
  const [mediaRecorder, setMediaRecorder] = useState(null)
  const [results, setResults] = useState([])

  const suggestedQuestions = [
    "Explain photosynthesis in simple terms",
    "Help me solve quadratic equations",
    "What are the main causes of World War I?",
    "Explain the concept of derivatives in calculus"
  ]

  // Chat functionality with VALIDATION
  const handleSendMessage = async () => {
    if (!message.trim() || isLoading) return

    const userMessage = { type: 'user', content: message, timestamp: new Date() }
    setChatHistory(prev => [...prev, userMessage])
    setIsLoading(true)
    setMessage('')

    try {
      // Use chatService which handles validation
      const result = await chatService.sendMessage(message, chatHistory.slice(-6).map(item => `${item.type}: ${item.content}`).join('\n'))

      let aiMessage
      
      // Check if query was rejected
      if (result.isRejected) {
        aiMessage = {
          type: 'ai',
          content: result.message || 'This assistant only answers study-related questions.',
          timestamp: new Date(),
          isRejected: true
        }
      } else if (result.success) {
        aiMessage = {
          type: 'ai',
          content: result.response,
          timestamp: new Date(),
          isRejected: false
        }
      } else {
        aiMessage = {
          type: 'ai',
          content: result.message || 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date(),
          isError: true
        }
      }

      setChatHistory(prev => [...prev, aiMessage])
    } catch (error) {
      const errorMessage = {
        type: 'ai',
        content: 'Network error. Please check your connection.',
        timestamp: new Date(),
        isError: true
      }
      setChatHistory(prev => [...prev, errorMessage])
    }

    setIsLoading(false)
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const runStudyAction = async (action, title) => {
    if (isLoading) return
    setIsLoading(true)
    setResults([])
    try {
      const content = await action()
      setResults([{ title, content }])
    } catch (error) {
      setResults([{ title: 'Error', content: error.message }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSummarize = () => {
    if (!summarizeInput.trim()) return
    return runStudyAction(async () => (await post('/summarize/text', { text: summarizeInput })).summary, 'Summary')
  }
  const handleImageUpload = e => {
    const file = e.target.files[0]
    e.target.value = ''
    if (file) return runStudyAction(async () => (await upload('/summarize/image', file)).analysis, 'Image Analysis')
  }
  const handleAudioTranscription = blob => runStudyAction(
    async () => (await upload('/summarize/audio', blob, blob.type.includes('mp4') ? 'recording.mp4' : 'recording.webm')).transcription,
    'Audio Transcription',
  )
  const startAudioRecording = async () => {
    if (audioRecording || isLoading) return
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      recordingRef.current = recorder
      setMediaRecorder(recorder)
      setAudioRecording(true)
      const chunks = []
      recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data) }
      recorder.onstop = () => {
        stream.getTracks().forEach(track => track.stop())
        setAudioRecording(false)
        handleAudioTranscription(new Blob(chunks, { type: recorder.mimeType }))
      }
      recorder.start()
    } catch {
      stream?.getTracks().forEach(track => track.stop())
      setResults([{ title: 'Error', content: 'Recording is unavailable. Allow microphone access and use HTTPS or localhost.' }])
    }
  }
  const stopAudioRecording = () => {
    if (mediaRecorder?.state === 'recording') mediaRecorder.stop()
  }
  const handleSolveDoubt = () => {
    if (!doubtInput.trim()) return
    return runStudyAction(async () => (await post('/summarize/solve', { problem: doubtInput, type: 'doubt' })).solution, 'Solution')
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-800 mb-2">AI Study Assistant</h1>
        <p className="text-gray-600">Multiple ways to learn - chat, summarize, analyze images, solve doubts</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex space-x-2 mb-6 bg-gray-200 p-1 rounded-lg overflow-x-auto">
        {[
          { id: 'chat', label: 'Chat', icon: '💬' },
          { id: 'summarize', label: 'Summarize', icon: '📝' },
          { id: 'image', label: 'Image', icon: '🖼️' },
          { id: 'audio', label: 'Audio', icon: '🎤' },
          { id: 'doubt', label: 'Solve Doubt', icon: '❓' }
        ].map(tab => (
          <button
            key={tab.id}
            disabled={isLoading || audioRecording}
            onClick={() => setActiveTab(tab.id)}
            className={`py-2 px-3 rounded font-medium transition-colors whitespace-nowrap ${
              activeTab === tab.id
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            <span className="mr-1">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl shadow-lg overflow-hidden">
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <>
            <div className="h-96 overflow-y-auto p-6 bg-gray-50">
              {chatHistory.length === 0 ? (
                <div className="text-center text-gray-500 mt-20">
                  <div className="text-6xl mb-4">💬</div>
                  <p className="text-lg">Start a conversation! Ask me anything about your studies.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {chatHistory.map((msg, index) => (
                    <div key={index} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                        msg.type === 'user'
                          ? 'bg-blue-500 text-white'
                          : msg.isRejected
                          ? 'bg-amber-50 border-2 border-amber-400 text-amber-900'
                          : msg.isError
                          ? 'bg-red-50 border-2 border-red-400 text-red-900'
                          : 'bg-white text-gray-800 shadow-md'
                      }`}>
                        {msg.isRejected && (
                          <div className="flex items-center gap-2 mb-2 font-semibold text-sm">
                            <span>⚠️</span>
                            <span>Query Restricted</span>
                          </div>
                        )}
                        {msg.isError && (
                          <div className="flex items-center gap-2 mb-2 font-semibold text-sm">
                            <span>❌</span>
                            <span>Error</span>
                          </div>
                        )}
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        <p className={`text-xs mt-1 ${
                          msg.type === 'user' 
                            ? 'text-blue-100' 
                            : msg.isRejected 
                            ? 'text-amber-700'
                            : msg.isError
                            ? 'text-red-700'
                            : 'text-gray-500'
                        }`}>
                          {msg.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  ))}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white text-gray-800 shadow-md px-4 py-2 rounded-lg">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {chatHistory.length === 0 && (
              <div className="px-6 py-4 border-t bg-white">
                <p className="text-sm text-gray-600 mb-3">Try asking:</p>
                <div className="flex flex-wrap gap-2">
                  {suggestedQuestions.map((question, index) => (
                    <button
                      key={index}
                      onClick={() => setMessage(question)}
                      className="text-sm bg-blue-100 text-blue-700 px-3 py-1 rounded-full hover:bg-blue-200 transition-colors"
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="p-6 bg-white border-t">
              <div className="flex space-x-4">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your question here... (Press Enter to send)"
                  aria-label="Study question"
                  maxLength={2000}
                  className="min-w-0 flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  rows="2"
                  disabled={isLoading}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={isLoading || !message.trim()}
                  aria-label="Send question"
                  className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                >
                  {isLoading ? '⏳' : '🚀'}
                </button>
              </div>
            </div>
          </>
        )}

        {/* Summarize Tab */}
        {activeTab === 'summarize' && (
          <div className="p-6">
            <h2 className="text-xl font-bold mb-4">Text Summarization</h2>
            <textarea
              value={summarizeInput}
              onChange={(e) => setSummarizeInput(e.target.value)}
              placeholder="Paste text here to summarize..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="6"
            />
            <button
              onClick={handleSummarize}
              disabled={isLoading || !summarizeInput.trim()}
              className="mt-4 bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Summarizing...' : 'Summarize'}
            </button>
            {results.length > 0 && (
              <div className="mt-6 bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto">
                {results.map((result, index) => (
                  <div key={index}>
                    <h3 className="font-bold text-lg mb-2 text-blue-600">{result.title}</h3>
                    <p className="text-gray-700 whitespace-pre-wrap">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Image Tab */}
        {activeTab === 'image' && (
          <div className="p-6">
            <h2 className="text-xl font-bold mb-4">Image Analysis</h2>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <div className="text-6xl mb-4">🖼️</div>
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={handleImageUpload}
                disabled={isLoading}
                className="hidden"
                id="image-input"
              />
              <label
                htmlFor="image-input"
                className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 cursor-pointer inline-block"
              >
                Upload Image
              </label>
              <p className="text-gray-500 mt-4">Upload a photo of problems, diagrams, or notes to analyze</p>
            </div>
            {results.length > 0 && (
              <div className="mt-6 bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto">
                {results.map((result, index) => (
                  <div key={index}>
                    <h3 className="font-bold text-lg mb-2 text-green-600">{result.title}</h3>
                    <p className="text-gray-700 whitespace-pre-wrap">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Audio Tab */}
        {activeTab === 'audio' && (
          <div className="p-6">
            <h2 className="text-xl font-bold mb-4">Audio Transcription</h2>
            <div className="text-center">
              <div className="text-6xl mb-4">🎤</div>
              <button
                onClick={audioRecording ? stopAudioRecording : startAudioRecording}
                disabled={isLoading}
                className={`px-8 py-3 rounded-lg text-white font-bold text-lg transition-colors ${
                  audioRecording
                    ? 'bg-red-500 hover:bg-red-600'
                    : 'bg-blue-500 hover:bg-blue-600'
                }`}
              >
                {audioRecording ? '⏹️ Stop Recording' : '🎙️ Start Recording'}
              </button>
              <p className="text-gray-500 mt-4">Record your doubts or lecture notes to transcribe</p>
            </div>
            {results.length > 0 && (
              <div className="mt-6 bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto">
                {results.map((result, index) => (
                  <div key={index}>
                    <h3 className="font-bold text-lg mb-2 text-purple-600">{result.title}</h3>
                    <p className="text-gray-700 whitespace-pre-wrap">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Doubt Solving Tab */}
        {activeTab === 'doubt' && (
          <div className="p-6">
            <h2 className="text-xl font-bold mb-4">Solve Your Doubts</h2>
            <textarea
              value={doubtInput}
              onChange={(e) => setDoubtInput(e.target.value)}
              placeholder="Describe the problem or concept you're struggling with..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              rows="6"
            />
            <button
              onClick={handleSolveDoubt}
              disabled={isLoading || !doubtInput.trim()}
              className="mt-4 bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Solving...' : 'Get Help'}
            </button>
            {results.length > 0 && (
              <div className="mt-6 bg-gray-50 p-4 rounded-lg max-h-64 overflow-y-auto">
                {results.map((result, index) => (
                  <div key={index}>
                    <h3 className="font-bold text-lg mb-2 text-green-600">{result.title}</h3>
                    <p className="text-gray-700 whitespace-pre-wrap">{result.content}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default Study
