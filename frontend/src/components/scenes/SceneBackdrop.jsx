export default function SceneBackdrop({ scenes, opacities }) {
  return scenes.map((scene) => {
    const opacity = opacities[scene.key] || 0
    const isVisible = opacity > 0.001

    return (
      <div
        key={scene.key}
        className={`scene-layer scene-${scene.key}${isVisible ? ' is-visible' : ''}`}
        style={{ opacity }}
        aria-hidden="true"
      >
        <div className="scene-halo" aria-hidden="true" />
        <div className="scene-motion" aria-hidden="true" />
        <div className="scene-motion-secondary" aria-hidden="true" />
        {scene.key === 'night' && <div className="scene-meteor" aria-hidden="true" />}
      </div>
    )
  })
}
