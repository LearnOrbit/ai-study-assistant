import { useEffect, useState } from 'react'
import { post, request } from '../services/http'

export default function Flashcards() {
  const [decks, setDecks] = useState([]), [documents, setDocuments] = useState([])
  const [title, setTitle] = useState(''), [text, setText] = useState(''), [documentId, setDocumentId] = useState(''), [count, setCount] = useState(10)
  const [deck, setDeck] = useState(null), [revealed, setRevealed] = useState(false), [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [revision, setRevision] = useState(0), [offset, setOffset] = useState(0)
  useEffect(() => {
    let active = true
    Promise.all([request(`/flashcards/decks?offset=${offset}`), request('/documents/')]).then(([rows, docs]) => {
      if (active) { setDecks(rows); setDocuments(docs.filter(d => d.processing_status === 'completed')) }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [revision, offset])
  const due = deck?.cards.filter(c => new Date(c.due_at) <= new Date()) || []
  const card = due[0]
  async function action(fn) {
    setBusy(true); setError('')
    try { await fn(); setRevision(x => x + 1) } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  function open(id) { action(async () => { setDeck(await request(`/flashcards/decks/${id}`)); setRevealed(false); setEditing(null) }) }
  function generate(e) {
    e.preventDefault(); action(async () => {
      setDeck(await post('/flashcards/decks', { title, count: Number(count), ...(documentId ? { document_id: Number(documentId) } : { text }) }))
      setOffset(0); setRevealed(false); setEditing(null)
    })
  }
  function review(rating) { action(async () => {
    const updated = await post(`/flashcards/cards/${card.id}/review`, { rating, version: card.version })
    setDeck(d => ({ ...d, cards: d.cards.map(c => c.id === updated.id ? updated : c) })); setRevealed(false)
  }) }
  function save(e) { e.preventDefault(); action(async () => {
    const updated = await request(`/flashcards/cards/${editing.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editing) })
    setDeck(d => ({ ...d, cards: d.cards.map(c => c.id === updated.id ? updated : c) })); setEditing(null)
  }) }
  return <div className="max-w-5xl mx-auto px-4 py-8"><p className="text-blue-600 text-sm mb-2">MAKE IT STICK</p><h1 className="text-3xl mb-2">Flashcards</h1><p className="text-gray-600 mb-6">Turn notes into a deck. Recall, reveal, and review at your own pace.</p>
    {error && <p role="alert" className="bg-red-50 text-red-700 rounded-lg p-4 mb-4">{error}</p>}
    <form onSubmit={generate} className="bg-white rounded-xl shadow-lg p-6 space-y-4"><h2 className="text-xl">Create a deck</h2>
      <label className="block">Deck title<input disabled={busy} required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} className="block border rounded-lg p-3 w-full mt-2" placeholder="Biology: cell structure" /></label>
      <label className="block">Source<select disabled={busy} value={documentId} onChange={e => setDocumentId(e.target.value)} className="block border rounded-lg p-3 w-full mt-2"><option value="">Paste my notes</option>{documents.map(d => <option key={d.id} value={d.id}>{d.title}</option>)}</select></label>
      {!documentId && <label className="block">Notes<textarea disabled={busy} required maxLength={50000} rows={5} value={text} onChange={e => setText(e.target.value)} className="block border rounded-lg p-3 w-full mt-2" /></label>}
      <label className="block">Number of cards<input disabled={busy} type="number" min={3} max={20} required value={count} onChange={e => setCount(e.target.value)} className="block border rounded-lg p-3 mt-2" /></label><button disabled={busy || !title.trim() || (!documentId && !text.trim())} className="primary-action">{busy ? 'Working…' : 'Generate flashcards'}</button>
    </form>
    <section className="mt-8"><h2 className="text-xl mb-4">Your decks</h2>{!decks.length && <p>No decks on this page yet. Create one from your notes.</p>}<div className="grid sm:grid-cols-2 gap-3">{decks.map(d => <button disabled={busy} onClick={() => open(d.id)} key={d.id} className="bg-white rounded-xl p-5 text-left shadow-lg"><strong className="break-words">{d.title}</strong><span className="block text-sm text-gray-500 mt-2">{d.total} cards · {d.due} due</span></button>)}</div><div className="flex gap-4 mt-4"><button disabled={!offset || busy} onClick={() => setOffset(x => Math.max(0, x - 50))}>Previous decks</button><button disabled={decks.length < 50 || busy} onClick={() => setOffset(x => x + 50)}>Next decks</button><button disabled={busy} onClick={() => setRevision(x => x + 1)}>Refresh decks</button></div></section>
    {deck && <section className="bg-white rounded-xl shadow-lg p-6 mt-6"><h2 className="text-xl mb-3">{deck.title}</h2><p className="text-sm text-gray-500 mb-4">{due.length} cards due · AI-generated cards can be edited below.</p>
      {card ? <div aria-live="polite"><h3 className="text-2xl my-6 whitespace-pre-wrap break-words">{card.front}</h3>{revealed ? <><p className="p-4 bg-gray-50 rounded-lg whitespace-pre-wrap break-words">{card.back}</p><p className="text-sm mt-4">How well did you remember?</p><div className="flex flex-wrap gap-3 mt-3">{['again', 'hard', 'good', 'easy'].map(r => <button disabled={busy} key={r} className="primary-action" onClick={() => review(r)}>{r}</button>)}</div><p className="text-xs text-gray-500 mt-3">Again returns in 10 minutes. Other ratings schedule a later day.</p></> : <button disabled={busy} className="primary-action" onClick={() => setRevealed(true)}>Reveal answer</button>}</div> : <p className="p-4 bg-gray-50 rounded-lg">You’re caught up. Reopen the deck later to check for due cards.</p>}
      <details className="mt-6"><summary>Edit cards</summary><ul>{deck.cards.map(c => <li key={c.id} className="border-b py-3 flex gap-4 justify-between"><span className="break-words min-w-0">{c.front}</span><button disabled={busy} onClick={() => setEditing(c)}>Edit</button></li>)}</ul></details>
      {editing && <form onSubmit={save} className="space-y-3 mt-4"><label className="block">Question<textarea required disabled={busy} maxLength={2000} className="block border p-3 w-full" value={editing.front} onChange={e => setEditing({ ...editing, front: e.target.value })} /></label><label className="block">Answer<textarea required disabled={busy} maxLength={4000} className="block border p-3 w-full" value={editing.back} onChange={e => setEditing({ ...editing, back: e.target.value })} /></label><button disabled={busy} className="primary-action">Save card</button><button type="button" disabled={busy} onClick={() => setEditing(null)} className="ml-4">Cancel</button></form>}
      <button disabled={busy} className="mt-6 text-red-700" onClick={() => { if (window.confirm('Delete this deck and its review history?')) action(async () => { await request(`/flashcards/decks/${deck.id}`, { method: 'DELETE' }); setDeck(null) }) }}>Delete deck</button>
    </section>}
  </div>
}
