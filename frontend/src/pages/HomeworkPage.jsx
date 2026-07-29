import FileTypeIcon from '../components/FileTypeIcon'
import { formatFileSize } from '../utils/fileTypes'

const MAX_SUBMISSION_FILES = 5
const MAX_SUBMISSION_FILE_SIZE = 20 * 1024 * 1024
const MAX_SUBMISSION_TOTAL_SIZE = 50 * 1024 * 1024

function TrashIcon() {
  return (
    <svg className="button-icon" viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5" />
    </svg>
  )
}

function AttachmentCard({
  attachment,
  downloadBusy,
  language,
  onDownload,
  onPreview,
  previewBusy,
}) {
  const zh = language === 'zh'
  return (
    <div className="attachment-file-card">
      <FileTypeIcon file={attachment} />
      <div className="attachment-file-main">
        <strong title={attachment.filename}>{attachment.filename}</strong>
        {formatFileSize(attachment.file_size) && <span>{formatFileSize(attachment.file_size)}</span>}
      </div>
      <div className="attachment-file-actions">
        <button type="button" className="download-btn" disabled={previewBusy} onClick={onPreview}>
          {previewBusy ? (zh ? '打开中…' : 'Opening…') : (zh ? '预览' : 'Preview')}
        </button>
        <button type="button" className="download-btn" disabled={downloadBusy} onClick={onDownload}>
          {downloadBusy ? (zh ? '下载中…' : 'Downloading…') : (zh ? '下载' : 'Download')}
        </button>
      </div>
    </div>
  )
}

export default function HomeworkPage({ model }) {
  const {
    activeClassId,
    expandedHomeworkId,
    handleDeleteHomework,
    handleDownloadAttachment,
    handleDownloadSubmission,
    handleOpenHomeworkAttachment,
    handleOpenSubmissionAttachment,
    handlePublishHomework,
    handleSubmitHomework,
    handleToggleSubmissions,
    homeworkBusy,
    homeworkFiles,
    homeworkForm,
    homeworks,
    homeworkSubmissions,
    isActionPending,
    isStudent,
    isTeacher,
    language,
    setHomeworkFiles,
    setHomeworkForm,
    setSubmitDrafts,
    submitDrafts,
    t,
  } = model

  const addHomeworkFiles = event => {
    const selected = Array.from(event.target.files || [])
    setHomeworkFiles(current => {
      const existing = new Set(current.map(file => `${file.name}:${file.size}:${file.lastModified}`))
      return [
        ...current,
        ...selected.filter(file => !existing.has(`${file.name}:${file.size}:${file.lastModified}`)),
      ]
    })
    event.target.value = ''
  }

  const updateSubmissionDraft = (homeworkId, draft, changes) => {
    setSubmitDrafts(current => ({
      ...current,
      [homeworkId]: { ...draft, ...changes },
    }))
  }

  const addSubmissionFiles = (homework, draft, event) => {
    const selected = Array.from(event.target.files || [])
    event.target.value = ''
    const oversized = selected.find(file => file.size > MAX_SUBMISSION_FILE_SIZE)
    if (oversized) {
      window.alert(language === 'zh'
        ? `${oversized.name} 超过单个文件20MB限制`
        : `${oversized.name} exceeds the 20 MB per-file limit`)
      return
    }
    const currentFiles = draft.files || []
    const signatures = new Set(
      currentFiles.map(file => `${file.name}:${file.size}:${file.lastModified}`),
    )
    const merged = [
      ...currentFiles,
      ...selected.filter(file => !signatures.has(`${file.name}:${file.size}:${file.lastModified}`)),
    ]
    const retainedIds = draft.retainedAttachmentIds || []
    const retainedSet = new Set(retainedIds)
    const retainedSize = (homework.my_submission?.attachments || [])
      .filter(item => retainedSet.has(item.id))
      .reduce((total, item) => total + (item.file_size || 0), 0)
    if (retainedIds.length + merged.length > MAX_SUBMISSION_FILES) {
      window.alert(language === 'zh'
        ? '每份作业最多保留和上传5个附件'
        : 'A submission can contain at most 5 attachments')
      return
    }
    const totalSize = retainedSize + merged.reduce((total, file) => total + file.size, 0)
    if (totalSize > MAX_SUBMISSION_TOTAL_SIZE) {
      window.alert(language === 'zh'
        ? '全部附件合计不能超过50MB'
        : 'All attachments together cannot exceed 50 MB')
      return
    }
    updateSubmissionDraft(homework.id, draft, { files: merged })
  }

  return (
    <section id="section-homework" className="section section-homework">
            <div className="resources-container">
              <div className="resources-header">
                <h2>{t.homeworkPageTitle}</h2>
              </div>

              <div className="homework-panel">
                {isTeacher && activeClassId && (
                  <div className="homework-publish">
                    <input
                      value={homeworkForm.title}
                      onChange={e => setHomeworkForm(p => ({ ...p, title: e.target.value }))}
                      placeholder={t.auth.homeworkName}
                    />
                    <textarea
                      value={homeworkForm.description}
                      onChange={e => setHomeworkForm(p => ({ ...p, description: e.target.value }))}
                      placeholder={t.auth.homeworkDesc}
                      rows={3}
                    />
                    <div className="homework-publish-row">
                      <label className="homework-due-field">
                        <span>{t.auth.homeworkDueLabel}</span>
                        <input
                          type="datetime-local"
                          value={homeworkForm.dueAt}
                          onChange={e => setHomeworkForm(p => ({ ...p, dueAt: e.target.value }))}
                        />
                      </label>
                      <label className="upload-btn soft">
                        {homeworkFiles.length > 0
                          ? t.auth.homeworkFilesSelected.replace('{count}', homeworkFiles.length)
                          : t.auth.homeworkAttach}
                        <input
                          type="file"
                          multiple
                          accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                          className="visually-hidden-file-input"
                          disabled={homeworkBusy}
                          onChange={addHomeworkFiles}
                        />
                      </label>
                      <button
                        type="button"
                        className="action-btn action-btn-primary"
                        disabled={homeworkBusy || !homeworkForm.title.trim()}
                        aria-busy={isActionPending('homework:publish')}
                        onClick={handlePublishHomework}
                      >
                        {isActionPending('homework:publish') ? t.auth.publishing : t.auth.publishHomework}
                      </button>
                    </div>
                    {homeworkFiles.length > 0 && (
                      <div className="homework-selected-files" aria-label={t.auth.selectedAttachments}>
                        {homeworkFiles.map((file, index) => (
                          <div key={`${file.name}:${file.size}:${file.lastModified}`} className="homework-selected-file">
                            <span>{file.name}</span>
                            <button
                              type="button"
                              className="download-btn danger"
                              disabled={homeworkBusy}
                              onClick={() => setHomeworkFiles(current => current.filter((_, fileIndex) => fileIndex !== index))}
                            >
                              {t.auth.removeAttachment}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {!activeClassId ? (
                  <p className="muted">{t.auth.noClasses}</p>
                ) : homeworks.length === 0 ? (
                  <p className="muted">{t.auth.noHomework}</p>
                ) : (
                  <div className="homework-list">
                    {homeworks.map(hw => {
                      const existingSubmissionAttachments = hw.my_submission?.attachments || []
                      const draft = submitDrafts[hw.id] || {
                        content: hw.my_submission?.content || '',
                        files: [],
                        retainedAttachmentIds: existingSubmissionAttachments.map(item => item.id),
                      }
                      const retainedAttachmentSet = new Set(draft.retainedAttachmentIds || [])
                      const subs = homeworkSubmissions[hw.id] || []
                      return (
                        <div key={hw.id} className="homework-card">
                          <div className="homework-card-top">
                            <div>
                              <h4>{hw.title}</h4>
                              {hw.description && <p className="homework-desc">{hw.description}</p>}
                              <div className="homework-meta">
                                {hw.due_at && <span>{t.auth.homeworkDue}: {hw.due_at.slice(0, 16).replace('T', ' ')}</span>}
                                {isTeacher && <span>{hw.submission_count} {t.auth.submissionCount}</span>}
                                {isStudent && (
                                  <span className={hw.my_submission ? 'status-done' : 'status-pending'}>
                                    {hw.my_submission ? t.auth.submitted : t.auth.notSubmitted}
                                  </span>
                                )}
                              </div>
                              {hw.attachments?.length > 0 && (
                                <div className="homework-attachments">
                                  <strong>{t.auth.homeworkAttachments}</strong>
                                  <div className="attachment-file-grid">
                                    {hw.attachments.map(attachment => (
                                      <AttachmentCard
                                        key={attachment.id}
                                        attachment={attachment}
                                        language={language}
                                        previewBusy={isActionPending(`homework:attachment:view:${attachment.id}`)}
                                        downloadBusy={isActionPending(`homework:attachment:download:${attachment.id}`)}
                                        onPreview={() => handleOpenHomeworkAttachment(hw, attachment, false)}
                                        onDownload={() => handleOpenHomeworkAttachment(hw, attachment, true)}
                                      />
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                            <div className="homework-card-actions">
                              {hw.has_attachment && !hw.attachments?.length && (
                                <button type="button" className="download-btn" disabled={isActionPending(`homework:attachment:${hw.id}`)} aria-busy={isActionPending(`homework:attachment:${hw.id}`)} onClick={() => handleDownloadAttachment(hw)}>
                                  {isActionPending(`homework:attachment:${hw.id}`) ? t.auth.downloading : t.auth.downloadAttachment}
                                </button>
                              )}
                              {isTeacher && (
                                <>
                                  <button type="button" className="download-btn" disabled={isActionPending(`homework:submissions:${hw.id}`)} aria-busy={isActionPending(`homework:submissions:${hw.id}`)} onClick={() => handleToggleSubmissions(hw.id)}>
                                    {isActionPending(`homework:submissions:${hw.id}`) ? t.auth.loading : (expandedHomeworkId === hw.id ? t.auth.hideSubmissions : t.auth.viewSubmissions)}
                                  </button>
                                  <button type="button" className="download-btn danger" disabled={isActionPending(`homework:delete:${hw.id}`)} aria-busy={isActionPending(`homework:delete:${hw.id}`)} onClick={() => handleDeleteHomework(hw.id)}>
                                    <TrashIcon />
                                    {isActionPending(`homework:delete:${hw.id}`) ? t.auth.deleting : t.auth.deleteHomework}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>

                          {isStudent && (
                            <div className="homework-submit">
                              <textarea
                                value={draft.content || ''}
                                onChange={event => updateSubmissionDraft(
                                  hw.id,
                                  draft,
                                  { content: event.target.value },
                                )}
                                placeholder={t.auth.submissionNote}
                                rows={2}
                              />
                              <div className="homework-publish-row">
                                <label className="upload-btn soft">
                                  {(draft.files || []).length > 0
                                    ? (language === 'zh'
                                      ? `已选择${draft.files.length}个新附件`
                                      : `${draft.files.length} new attachments`)
                                    : t.auth.uploadSubmission}
                                  <input
                                    type="file"
                                    multiple
                                    accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                                    className="visually-hidden-file-input"
                                    disabled={homeworkBusy}
                                    onChange={event => addSubmissionFiles(hw, draft, event)}
                                  />
                                </label>
                                <button
                                  type="button"
                                  className="action-btn action-btn-primary"
                                  disabled={
                                    homeworkBusy
                                    || (
                                      !(draft.content || '').trim()
                                      && retainedAttachmentSet.size === 0
                                      && (draft.files || []).length === 0
                                    )
                                  }
                                  aria-busy={isActionPending(`homework:submit:${hw.id}`)}
                                  onClick={() => handleSubmitHomework(hw.id)}
                                >
                                  {isActionPending(`homework:submit:${hw.id}`) ? t.auth.submitting : (hw.my_submission ? t.auth.resubmitHomework : t.auth.submitHomework)}
                                </button>
                              </div>
                              {(existingSubmissionAttachments.length > 0 || (draft.files || []).length > 0) && (
                                <div className="submission-draft-files">
                                  {existingSubmissionAttachments.map(attachment => {
                                    const retained = retainedAttachmentSet.has(attachment.id)
                                    return (
                                      <div key={attachment.id} className={`submission-draft-file${retained ? '' : ' is-removed'}`}>
                                        <FileTypeIcon file={attachment} />
                                        <div>
                                          <strong>{attachment.filename}</strong>
                                          <span>
                                            {retained
                                              ? (language === 'zh' ? '已有附件' : 'Existing attachment')
                                              : (language === 'zh' ? '提交后移除' : 'Will be removed')}
                                          </span>
                                        </div>
                                        <button
                                          type="button"
                                          className={retained ? 'download-btn danger' : 'download-btn'}
                                          onClick={() => updateSubmissionDraft(hw.id, draft, {
                                            retainedAttachmentIds: retained
                                              ? (draft.retainedAttachmentIds || []).filter(id => id !== attachment.id)
                                              : [...(draft.retainedAttachmentIds || []), attachment.id],
                                          })}
                                        >
                                          {retained && <TrashIcon />}
                                          {retained
                                            ? (language === 'zh' ? '移除' : 'Remove')
                                            : (language === 'zh' ? '恢复' : 'Restore')}
                                        </button>
                                      </div>
                                    )
                                  })}
                                  {(draft.files || []).map((file, index) => (
                                    <div key={`${file.name}:${file.size}:${file.lastModified}`} className="submission-draft-file">
                                      <FileTypeIcon file={{ filename: file.name }} />
                                      <div>
                                        <strong>{file.name}</strong>
                                        <span>{language === 'zh' ? '新附件' : 'New attachment'} · {formatFileSize(file.size)}</span>
                                      </div>
                                      <button
                                        type="button"
                                        className="download-btn danger"
                                        onClick={() => updateSubmissionDraft(hw.id, draft, {
                                          files: (draft.files || []).filter((_, fileIndex) => fileIndex !== index),
                                        })}
                                      >
                                        <TrashIcon />
                                        {language === 'zh' ? '移除' : 'Remove'}
                                      </button>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}

                          {isTeacher && expandedHomeworkId === hw.id && (
                            <div className="submission-list">
                              <div className="submission-list-heading">
                                <strong>{language === 'zh' ? `学生提交（${subs.length}）` : `Student submissions (${subs.length})`}</strong>
                              </div>
                              {subs.length === 0 ? (
                                <p className="muted">{t.auth.noHomework}</p>
                              ) : subs.map(sub => {
                                const attachmentCount = sub.attachments?.length || (sub.has_file ? 1 : 0)
                                return (
                                <article key={sub.id} className="submission-card">
                                  <header className="submission-card-header">
                                    <div className="submission-student-mark" aria-hidden="true">
                                      {(sub.student_name || '?').trim().slice(0, 1).toUpperCase()}
                                    </div>
                                    <div className="submission-student">
                                      <strong>{sub.student_name}</strong>
                                      <span>{sub.submitted_at?.slice(0, 16).replace('T', ' ')}</span>
                                    </div>
                                    {attachmentCount > 0 && (
                                      <span className="submission-attachment-count">
                                        {language === 'zh'
                                          ? `${attachmentCount}个附件`
                                          : `${attachmentCount} attachments`}
                                      </span>
                                    )}
                                  </header>
                                  {sub.content && (
                                    <p className="submission-text">{sub.content}</p>
                                  )}
                                  {sub.attachments?.length > 0 && (
                                    <div className="attachment-file-grid submission-attachment-grid">
                                      {sub.attachments.map(attachment => (
                                        <AttachmentCard
                                          key={attachment.id}
                                          attachment={attachment}
                                          language={language}
                                          previewBusy={isActionPending(`submission:attachment:view:${attachment.id}`)}
                                          downloadBusy={isActionPending(`submission:attachment:download:${attachment.id}`)}
                                          onPreview={() => handleOpenSubmissionAttachment(sub, attachment, false)}
                                          onDownload={() => handleOpenSubmissionAttachment(sub, attachment, true)}
                                        />
                                      ))}
                                    </div>
                                  )}
                                  {sub.has_file && !sub.attachments?.length && (
                                    <div className="submission-legacy-file">
                                      <button type="button" className="download-btn" disabled={isActionPending(`submission:download:${sub.id}`)} aria-busy={isActionPending(`submission:download:${sub.id}`)} onClick={() => handleDownloadSubmission(sub)}>
                                        {isActionPending(`submission:download:${sub.id}`) ? t.auth.downloading : (sub.filename || t.download)}
                                      </button>
                                    </div>
                                  )}
                                </article>
                                )
                              })}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          </section>
  )
}
