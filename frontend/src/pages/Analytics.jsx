import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../services/http'

export default function Analytics() {
  const [range, setRange] = useState('week')
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    request(`/analytics?range=${range}`).then(data => { if (active) setData(data) })
      .catch(error => { if (active) setError(error.message) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [range, revision])
  return <div className="container mx-auto px-4 py-8 max-w-7xl">
    <h1 className="text-3xl text-gray-800 mb-2">Your learning, in perspective</h1>
    <p className="text-gray-600 mb-7">Practice, problem solving, flashcard reviews, and library activity in one place.</p>
    <div className="flex flex-wrap gap-3 mb-7" aria-label="Reporting period">{['week', 'month', 'semester'].map(value => <button key={value} aria-pressed={range === value} onClick={() => setRange(value)} className={`px-4 py-2 rounded-lg ${range === value ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700'}`}>{value === 'week' ? 'Last 7 days' : value === 'month' ? 'Last 30 days' : 'Last 180 days'}</button>)}</div>
    {loading ? <p role="status">Loading your learning insights…</p> : error ? <div role="alert" className="bg-red-50 text-red-700 p-5 rounded-lg"><p>{error}</p><button className="underline mt-3" onClick={() => setRevision(revision + 1)}>Try again</button></div> : data && <>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-7">{[[data.attempts, 'Practice attempts'], [data.correct, 'Correct answers'], [data.accuracy === null ? '—' : `${data.accuracy}%`, 'Answer accuracy'], [data.documents, 'Documents uploaded'], [data.solutions, 'Problems explored'], [data.reviews, 'Flashcard reviews'], [data.active_days, 'Active days in period'], [data.streak, 'Current streak · UTC days']].map(([value, label]) => <section key={label} className="bg-white rounded-xl shadow-lg p-6"><p className="text-3xl font-semibold text-blue-600 mb-3">{value}</p><h2 className="text-sm text-gray-600">{label}</h2></section>)}</div>
      {data.attempts === 0 && <div className="bg-white rounded-xl shadow-lg p-6 mb-7"><h2 className="text-xl mb-2">Your progress starts with one question.</h2><p className="text-gray-600 mb-4">Complete a practice exercise to see your accuracy and subject results here.</p><Link className="primary-action" to="/practice">Start practicing</Link></div>}
      <div className="grid lg:grid-cols-2 gap-6 mb-7"><section className="bg-white rounded-xl shadow-lg p-6"><h2 className="text-xl mb-5">Accuracy by subject</h2>{data.subjects.map(subject => <div key={subject.subject} className="mb-5"><div className="flex justify-between gap-2 text-sm mb-2"><span>{subject.subject}</span><span>{subject.score === null ? 'No attempts yet' : `${subject.score}% · ${subject.attempts} ${subject.attempts === 1 ? 'attempt' : 'attempts'}`}</span></div><div className="h-2 rounded bg-gray-200"><div className="h-2 rounded bg-blue-500" style={{ width: `${subject.score || 0}%` }} /></div></div>)}</section>
      <section className="bg-white rounded-xl shadow-lg p-6"><h2 className="text-xl mb-2">Activity in this period</h2><p className="text-sm text-gray-600 mb-4">Actions per day · UTC · practice, solutions, reviews, uploads</p><div className="flex items-end gap-3 h-48 overflow-x-auto">{data.daily.map(day => <div key={day.date} className="flex-1 text-center" style={{ minWidth: 32 }}><span className="text-xs">{day.total}</span><div className="bg-blue-500 rounded-t mt-2" style={{ height: `${day.total / Math.max(1, ...data.daily.map(item => item.total)) * 115}px` }} /><span className="text-xs text-gray-600">{new Date(`${day.date}T12:00:00Z`).toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })}</span></div>)}</div></section></div>
      <section className="bg-white rounded-xl shadow-lg p-6 mb-7"><h2 className="text-xl mb-3">Flashcard recall</h2><p className="text-sm text-gray-600 mb-4">Your self-reported recall, separate from graded practice accuracy.</p><div className="grid grid-cols-2 sm:grid-cols-4 gap-3">{Object.entries(data.review_ratings).map(([rating, count]) => <div key={rating} className="bg-gray-50 rounded-lg p-4"><strong className="text-2xl">{count}</strong><p>{rating}</p></div>)}</div><p className="text-xs text-gray-500 mt-4">Streaks count consecutive UTC days with any recorded activity, ending today or yesterday. Deleted solutions and decks are removed from these totals.</p></section>
      <section className="bg-white rounded-xl shadow-lg p-6"><h2 className="text-xl mb-5">Recent activity</h2>{data.activity.length ? <ul className="space-y-3">{data.activity.map((item, index) => <li key={`${item.date}-${index}`} className="flex flex-wrap justify-between gap-3 p-4 bg-gray-50 rounded-lg"><div className="min-w-0"><p className="break-words">{item.activity}</p><p className="text-xs text-gray-500 mt-1">{new Date(item.date).toLocaleString()}</p></div><span className="text-sm text-blue-600">{item.result}</span></li>)}</ul> : <p className="text-gray-600">No activity in this period. Upload notes or complete a practice question to get started.</p>}</section>
    </>}
  </div>
}
