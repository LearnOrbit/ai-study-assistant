import { useState } from 'react'
import { Link } from 'react-router-dom'
import { request, post } from '../services/http'

const subjects = [
  { id: 'math', name: 'Mathematics', icon: '🔢', topics: 'Algebra · Calculus · Statistics' },
  { id: 'physics', name: 'Physics', icon: '⚛️', topics: 'Motion · Forces · Energy' },
  { id: 'chemistry', name: 'Chemistry', icon: '⚗️', topics: 'Equations · Acids · Atoms' },
  { id: 'biology', name: 'Biology', icon: '🧬', topics: 'Cells · Genetics · Photosynthesis' },
]
export default function Practice() {
  const [subject, setSubject] = useState(null)
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [option, setOption] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [finished, setFinished] = useState(false)
  const question = questions[index]

  async function start(selected) {
    setBusy(true)
    setError('')
    try {
      const data = await request(`/practice/${selected.id}`)
      setQuestions(data.questions)
      setSubject(selected)
      setIndex(0)
      setOption(null)
      setResult(null)
      setFinished(false)
    } catch (error) { setError(error.message) }
    finally { setBusy(false) }
  }
  async function check() {
    if (option === null || busy || result) return
    setBusy(true)
    setError('')
    try { setResult(await post('/practice/attempts', { question_id: question.id, option })) }
    catch (error) { setError(error.message) }
    finally { setBusy(false) }
  }
  function next() {
    if (index === questions.length - 1) setFinished(true)
    else { setIndex(index + 1); setOption(null); setResult(null); setError('') }
  }
  return <div className="container mx-auto px-4 py-8 max-w-6xl">
    <h1 className="text-3xl text-gray-800 mb-2">{subject ? `${subject.name} practice` : 'Practice with purpose'}</h1>
    <p className="text-gray-600 mb-8">Curated introductory exercises, clear explanations, and progress saved as you go.</p>
    {error && <p role="alert" className="bg-red-50 text-red-700 rounded-lg p-4 mb-4">{error}</p>}
    {busy && <p role="status" className="text-gray-600 mb-4">{subject ? 'Saving your answer…' : 'Loading exercises…'}</p>}
    {!subject ? <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5">{subjects.map(item => <section className="bg-white rounded-xl shadow-lg p-6" key={item.id}>
      <span className="text-4xl">{item.icon}</span><h2 className="text-xl font-semibold mt-5 mb-3">{item.name}</h2>
      <p className="text-sm text-gray-600 mb-6">{item.topics}</p><p className="text-xs text-gray-500 mb-4">3 introductory questions</p>
      <button disabled={busy} onClick={() => start(item)} className="bg-blue-500 text-white rounded-lg px-4 py-3 w-full disabled:opacity-50">Start practice</button>
    </section>)}</div> : <>
      <button disabled={busy} onClick={() => { setSubject(null); setError('') }} className="text-blue-600 mb-5">← All subjects</button>
      {finished ? <section className="bg-white rounded-xl shadow-lg p-8"><h2 className="text-2xl mb-3">Practice complete</h2><p className="text-gray-600 mb-5">Your answers have been saved. Review your results or try another subject.</p><Link to="/analytics" className="primary-action">View learning insights</Link></section> : question && <section className="bg-white rounded-xl shadow-lg p-6 md:p-8 max-w-3xl">
        <p className="text-sm text-gray-500 mb-3">Question {index + 1} of {questions.length}</p><h2 className="text-xl mb-6">{question.question}</h2>
        <fieldset disabled={busy || !!result} className="space-y-3"><legend className="text-sm text-gray-600 mb-3">Choose your answer</legend>{question.options.map((answer, i) => <label key={i} className={`flex items-center gap-3 p-4 rounded-lg border cursor-pointer ${option === i ? 'border-green-700 bg-green-50' : 'border-gray-200'}`}><input type="radio" name="answer" checked={option === i} onChange={() => setOption(i)} /><span>{answer}</span></label>)}</fieldset>
        {!result ? <button disabled={option === null || busy} onClick={check} className="primary-action mt-6 disabled:opacity-50">Check answer</button> : <div role="status" className="mt-6 border-t pt-6"><h3 className="font-semibold mb-3">{result.correct ? 'Correct — nicely done.' : `Keep learning. The answer is ${result.answer}.`}</h3><p className="text-gray-600 mb-5">{result.solution}</p><button onClick={next} className="primary-action">{index === questions.length - 1 ? 'Finish practice' : 'Next question'}</button></div>}
      </section>}
    </>}
    <section className="mt-10 bg-white rounded-xl shadow-lg p-7"><h2 className="text-xl mb-2">Have a problem of your own?</h2><p className="text-gray-600 mb-5">Bring it to your AI study companion for a step-by-step explanation.</p><div className="flex flex-wrap gap-4"><Link className="primary-action" to="/study?tab=image">Upload a problem</Link><Link className="primary-action" to="/study?tab=doubt">Ask the AI tutor</Link></div></section>
  </div>
}
