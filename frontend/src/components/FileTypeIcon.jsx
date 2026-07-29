import { getFileCategory } from '../utils/fileTypes'

const LABELS = {
  archive: 'ZIP',
  file: 'FILE',
  image: 'IMG',
  pdf: 'PDF',
  presentation: 'PPT',
  word: 'DOC',
}

export default function FileTypeIcon({ file, size = 'medium' }) {
  const category = getFileCategory(file)
  return (
    <span className={`file-type-icon is-${category} is-${size}`} aria-hidden="true">
      <svg viewBox="0 0 28 32" focusable="false">
        <path d="M5 1.5h11l7 7V29a1.5 1.5 0 0 1-1.5 1.5h-16A1.5 1.5 0 0 1 4 29V3A1.5 1.5 0 0 1 5.5 1.5Z" />
        <path d="M16 1.5v7h7" />
      </svg>
      <small>{LABELS[category]}</small>
    </span>
  )
}
