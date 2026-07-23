function LineIcon({ type }) {
  if (type === 'day') return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  )
  if (type === 'sunset') return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <path d="M17 18a5 5 0 0 0-10 0M2 18h20M2 22h20M8 22h8" />
      <path d="M12 2v3M4.93 4.93l1.41 1.41M19.07 4.93l-1.41 1.41" />
    </svg>
  )
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="line-icon">
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
    </svg>
  )
}

export default function SceneSwitcher({ scenes, activeScene, rotation, dragging, opacity, language, onMouseDown, onSceneSelect }) {
  return (
    <div className="scene-dial-wrap" style={{ opacity }}>
      <div className="dial-pointer" aria-hidden="true" />
      <div
        className="scene-dial"
        onMouseDown={onMouseDown}
        style={{
          transform: `rotate(${rotation}deg)`,
          cursor: dragging ? 'grabbing' : 'grab',
          transition: dragging ? 'none' : 'transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)',
        }}
      >
        <div className="dial-divider" style={{ transform: 'rotate(60deg)' }} />
        <div className="dial-divider" style={{ transform: 'rotate(180deg)' }} />
        <div className="dial-divider" style={{ transform: 'rotate(300deg)' }} />
        {scenes.map((scene, index) => (
          <button
            key={scene.key}
            type="button"
            className={`dial-item ${activeScene === scene.key ? 'active' : ''}`}
            style={{ transform: `rotate(${index * 120}deg) translateY(-38px) rotate(${-index * 120 - rotation}deg)` }}
            onMouseDown={(event) => event.stopPropagation()}
            onClick={() => onSceneSelect(scene.key)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault()
                onSceneSelect(scene.key)
              }
            }}
            aria-label={scene.label[language]}
            aria-pressed={activeScene === scene.key}
            title={scene.label[language]}
          >
            <LineIcon type={scene.key} />
          </button>
        ))}
      </div>
    </div>
  )
}
