// Only transform prose. Code spans and fenced graph data must remain byte-for-byte intact.
export function prepareMathContent(content = '', streaming = false) {
  let output = '', buffer = '', mode = null, delimiter = ''
  let incomplete = false
  const normalize = text => text.replace(/\\\(([\s\S]*?)\\\)/g, (_, expr) => `$${expr}$`).replace(/\\\[([\s\S]*?)\\\]/g, (_, expr) => `\n$$\n${expr}\n$$\n`)
  const flush = () => { output += normalize(buffer); buffer = '' }
  for (let i = 0; i < content.length;) {
    if (mode === 'code') {
      const end = content.indexOf(delimiter, i)
      if (end < 0) { buffer += content.slice(i); incomplete = true; break }
      output += buffer + content.slice(i, end + delimiter.length)
      buffer = ''; mode = null; i = end + delimiter.length
      continue
    }
    if (mode === 'math') {
      const end = content.indexOf(delimiter, i)
      if (end < 0) { buffer += content.slice(i); incomplete = true; break }
      output += normalize(buffer + content.slice(i, end + delimiter.length))
      buffer = ''; mode = null; i = end + delimiter.length
      continue
    }
    const rest = content.slice(i)
    const code = /^(`{1,}|~{3,})/.exec(rest)
    const math = rest.startsWith('$$') ? ['$$', '$$'] : rest.startsWith('$') && content[i-1] !== '\\' ? ['$', '$'] : rest.startsWith('\\(') ? ['\\(', '\\)'] : rest.startsWith('\\[') ? ['\\[', '\\]'] : null
    if (code) { flush(); mode = 'code'; delimiter = code[1]; buffer = delimiter; i += delimiter.length }
    else if (math) { flush(); mode = 'math'; delimiter = math[1]; buffer = math[0]; i += math[0].length }
    else { buffer += content[i]; i++ }
  }
  if (mode) {
    // Never invent a closing delimiter or a missing mathematical expression.
    if (!streaming) output += '\n\n' + (mode === 'math' ? '（公式未完整生成，请重新生成回答。）' : '（代码或图形未完整生成，请重新生成回答。）')
  } else flush()
  return { content: output, incomplete }
}
