import { getFileCategory } from '../utils/fileTypes'

function FileCategoryMark({ category }) {
  if (category === 'pdf') {
    return (
      <path
        className="file-icon-mark is-stroke"
        d="M8.2 22.9c2.5-4.1 4.1-8 4.4-11.4.6 3.9 2.5 7.3 5.8 9.8-3.9-.7-7.5-.2-10.2 1.6Zm4.2-3.9c1.4-.3 2.8-.4 4.2-.2a15.7 15.7 0 0 1-2.8-4.3c-.3 1.5-.8 3-1.4 4.5Z"
      />
    )
  }
  if (category === 'presentation') {
    return (
      <>
        <rect className="file-icon-mark is-stroke" x="7.8" y="11.7" width="12.4" height="10" rx="1" />
        <circle className="file-icon-mark is-fill" cx="12" cy="16.7" r="2.1" />
        <path className="file-icon-mark is-stroke" d="M15.7 14.4h2.1m-2.1 2.3h2.1m-2.1 2.3h2.1" />
      </>
    )
  }
  if (category === 'word') {
    return (
      <>
        <rect className="file-icon-mark is-fill" x="7.8" y="11.5" width="12.4" height="10.4" rx="1" />
        <path className="file-icon-mark is-light-stroke" d="M10.3 14.2h7.4m-7.4 2.5h7.4m-7.4 2.5h5.1" />
      </>
    )
  }
  if (category === 'image') {
    return (
      <>
        <rect className="file-icon-mark is-stroke" x="7.6" y="11.5" width="12.8" height="10.5" rx="1" />
        <circle className="file-icon-mark is-fill" cx="16.9" cy="14.7" r="1.2" />
        <path className="file-icon-mark is-stroke" d="m9.6 20 3.1-3.2 2.1 2 1.6-1.6 2.2 2.8" />
      </>
    )
  }
  if (category === 'archive') {
    return (
      <>
        <path className="file-icon-mark is-stroke" d="M11.8 10.5h4.4v2.2h-4.4zm0 4.2h4.4v2.2h-4.4zm0 4.2h4.4v3.4h-4.4z" />
        <path className="file-icon-mark is-stroke" d="M14 11.1v10.4" />
      </>
    )
  }
  return (
    <path className="file-icon-mark is-stroke" d="M8.8 13h9.6m-9.6 3.4h9.6m-9.6 3.4h6.3" />
  )
}

export default function FileTypeIcon({ file, size = 'medium' }) {
  const category = getFileCategory(file)
  return (
    <span className={`file-type-icon is-${category} is-${size}`} aria-hidden="true">
      <svg viewBox="0 0 28 32" focusable="false">
        <path className="file-icon-sheet" d="M5.5 1.5h11l6 6V29a1.5 1.5 0 0 1-1.5 1.5H5.5A1.5 1.5 0 0 1 4 29V3a1.5 1.5 0 0 1 1.5-1.5Z" />
        <path className="file-icon-fold" d="M16.5 1.5v6h6" />
        <FileCategoryMark category={category} />
      </svg>
    </span>
  )
}
