export default function SceneBackdrop({ scenes, opacities }) {
  return scenes.map((scene) => (
    <div key={scene.key} className={`scene-layer scene-${scene.key}`} style={{ opacity: opacities[scene.key] }}>
      <div className="scene-halo" aria-hidden="true" />
      <div className="scene-motion" aria-hidden="true" />
      <div className="scene-motion-secondary" aria-hidden="true" />
      {scene.key === 'night' && <div className="scene-meteor" aria-hidden="true" />}
    </div>
  ))
}
