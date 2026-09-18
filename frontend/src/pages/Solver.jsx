import { useEffect, useState } from 'react'
import { post, request } from '../services/http'

export default function Solver() {
  const [problem, setProblem] = useState('')
  const [subject, setSubject] = useState('math')
  const [file, setFile] = useState(null)
  const [result, setResult] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [history, setHistory] = useState([])
  const [offset, setOffset] = useState(0)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    let active = true
    request(`/problems/history?offset=${offset}`).then(rows => { if (active) setHistory(rows) })
      .catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [offset, revision])
  async function solve(event) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null); setRevealed(false)
    try {
      let data
      if (file) {
        if (file.size > 10 * 1024 * 1024) throw new Error('Choose an image smaller than 10 MB.')
        const body = new FormData(); body.append('file', file); body.append('subject', subject)
        data = await request('/problems/image', { method: 'POST', body })
      } else data = await post('/problems/solve', { problem, subject })
      setResult(data); setOffset(0); setRevision(x => x + 1)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function remove(id) {
    setBusy(true); setError('')
    try { await request(`/problems/${id}`, { method: 'DELETE' }); if (result?.id === id) setResult(null); setRevision(x => x + 1) }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="max-w-5xl mx-auto px-4 py-8">
    <p className="text-sm text-blue-600 mb-2">UNDERSTAND THE HOW</p><h1 className="text-3xl mb-2">Problem solver</h1>
    <p className="text-gray-600 mb-6">Start with a hint, then explore each step. Your solutions are saved for later.</p>
    {error && <p role="alert" className="p-4 mb-4 bg-red-50 text-red-700 rounded-xl">{error}</p>}
    <form onSubmit={solve} className="bg-white rounded-xl shadow-lg p-6 space-y-4">
      <label className="block">Subject<select disabled={busy} className="block border rounded-lg p-3 mt-2 w-full" value={subject} onChange={e => setSubject(e.target.value)}>{['math', 'physics', 'chemistry', 'biology', 'programming', 'other'].map(s => <option key={s} value={s}>{s}</option>)}</select></label>
      <label className="block">Your problem<textarea disabled={busy || !!file} required={!file} maxLength={20000} className="block border rounded-lg p-3 mt-2 w-full" rows={4} value={problem} onChange={e => setProblem(e.target.value)} placeholder="For example: solve 2x + 5 = 13" /></label>
      <label className="block">Or upload a problem photo<input disabled={busy} className="block mt-2 max-w-full" type="file" accept="image/png,image/jpeg,image/webp" onChange={e => setFile(e.target.files[0] || null)} /></label>
      <p className="text-sm text-gray-500">PNG, JPEG or WebP · up to 10 MB. A selected photo replaces the typed problem.</p>
      <button className="primary-action" disabled={busy || (!file && !problem.trim())}>{busy ? 'Working…' : 'Help me solve it'}</button>
    </form>
    {result && <section aria-live="polite" className="bg-white rounded-xl shadow-lg p-6 mt-6 break-words">
      <h2 className="text-xl mb-3">{result.problem}</h2><p className="bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">Hint: {result.hint}</p>
      {!revealed ? <button className="primary-action mt-4" onClick={() => setRevealed(true)}>Reveal solution</button> : <><ol className="list-decimal pl-6 space-y-3 my-5">{result.steps.map((step, i) => <li key={i} className="whitespace-pre-wrap">{step}</li>)}</ol><h3 className="font-semibold">Answer</h3><p className="whitespace-pre-wrap mb-4">{result.answer}</p><h3 className="font-semibold">Check the result</h3><p className="whitespace-pre-wrap">{result.verification}</p></>}
      <p className="text-xs text-gray-500 mt-5">AI-generated explanation. Check important steps against your course materials.</p>
    </section>}
    <section className="mt-8"><h2 className="text-xl mb-4">Saved solutions</h2>{history.length === 0 && <p className="text-gray-500">No saved solutions on this page yet.</p>}
      <ul className="space-y-3">{history.map(row => <li key={row.id} className="bg-white p-4 rounded-xl flex gap-4 justify-between"><button disabled={busy} className="text-left min-w-0 break-words" onClick={() => { setResult(row); setRevealed(false) }}>{row.problem}<span className="block text-xs text-gray-500 mt-1">{row.subject} · {new Date(row.created_at).toLocaleString()}</span></button><button disabled={busy} aria-label={`Delete solution: ${row.problem}`} onClick={() => remove(row.id)}>Delete</button></li>)}</ul>
      <div className="flex gap-4 mt-4"><button disabled={offset === 0 || busy} onClick={() => setOffset(x => Math.max(0, x - 20))}>Previous</button><button disabled={history.length < 20 || busy} onClick={() => setOffset(x => x + 20)}>Next</button><button disabled={busy} onClick={() => setRevision(x => x + 1)}>Refresh history</button></div>
    </section>
  </div>
}
