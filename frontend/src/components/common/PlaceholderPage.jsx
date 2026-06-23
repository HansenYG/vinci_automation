import { PageHeader } from '../layout/Layout'

// Consistent scaffold for not-yet-built phases. `features` lists what's coming;
// `children` optionally renders a live preview when the backend already supports it.
export default function PlaceholderPage({ title, subtitle, phase, features = [], children }) {
  return (
    <>
      <PageHeader title={title} subtitle={subtitle} actions={<span className="badge blue">{phase}</span>} />
      <div className="content">
        <div className="card" style={{ padding: 24, maxWidth: 760 }}>
          <h3 style={{ marginTop: 0 }}>Planned for {phase}</h3>
          <ul style={{ margin: 0, paddingLeft: 18, color: 'var(--muted)', lineHeight: 1.9, fontSize: 14 }}>
            {features.map((f) => <li key={f}>{f}</li>)}
          </ul>
          <p className="muted" style={{ fontSize: 13, marginBottom: 0, marginTop: 16 }}>
            This route, its sidebar entry and the backend endpoints are scaffolded now so the
            phase can be built without restructuring.
          </p>
        </div>
        {children}
      </div>
    </>
  )
}
