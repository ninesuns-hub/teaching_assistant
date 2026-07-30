export function showDateTimePicker(input) {
  if (typeof input?.showPicker !== 'function') return false

  try {
    input.showPicker()
    return true
  } catch {
    return false
  }
}
