

export default function HomeworkPage({ model }) {
  const { activeClassId, expandedHomeworkId, handleDeleteHomework, handleDownloadAttachment, handleDownloadSubmission, handlePublishHomework, handleSubmitHomework, handleToggleSubmissions, homeworkBusy, homeworkFile, homeworkForm, homeworks, homeworkSubmissions, isStudent, isTeacher, setHomeworkFile, setHomeworkForm, setSubmitDrafts, submitDrafts, t } = model

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
                      <input
                        type="datetime-local"
                        value={homeworkForm.dueAt}
                        onChange={e => setHomeworkForm(p => ({ ...p, dueAt: e.target.value }))}
                        aria-label={t.auth.homeworkDue}
                      />
                      <label className="upload-btn soft">
                        {homeworkFile ? homeworkFile.name : t.auth.homeworkAttach}
                        <input
                          type="file"
                          accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                          hidden
                          onChange={e => setHomeworkFile(e.target.files?.[0] || null)}
                        />
                      </label>
                      <button
                        type="button"
                        className="action-btn action-btn-primary"
                        disabled={homeworkBusy || !homeworkForm.title.trim()}
                        onClick={handlePublishHomework}
                      >
                        {t.auth.publishHomework}
                      </button>
                    </div>
                  </div>
                )}

                {!activeClassId ? (
                  <p className="muted">{t.auth.noClasses}</p>
                ) : homeworks.length === 0 ? (
                  <p className="muted">{t.auth.noHomework}</p>
                ) : (
                  <div className="homework-list">
                    {homeworks.map(hw => {
                      const draft = submitDrafts[hw.id] || {}
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
                            </div>
                            <div className="homework-card-actions">
                              {hw.has_attachment && (
                                <button type="button" className="download-btn" onClick={() => handleDownloadAttachment(hw)}>
                                  {t.auth.downloadAttachment}
                                </button>
                              )}
                              {isTeacher && (
                                <>
                                  <button type="button" className="download-btn" onClick={() => handleToggleSubmissions(hw.id)}>
                                    {expandedHomeworkId === hw.id ? t.auth.hideSubmissions : t.auth.viewSubmissions}
                                  </button>
                                  <button type="button" className="download-btn danger" onClick={() => handleDeleteHomework(hw.id)}>
                                    {t.auth.deleteHomework}
                                  </button>
                                </>
                              )}
                            </div>
                          </div>

                          {isStudent && (
                            <div className="homework-submit">
                              <textarea
                                value={draft.content || ''}
                                onChange={e => setSubmitDrafts(prev => ({
                                  ...prev,
                                  [hw.id]: { ...draft, content: e.target.value },
                                }))}
                                placeholder={t.auth.submissionNote}
                                rows={2}
                              />
                              <div className="homework-publish-row">
                                <label className="upload-btn soft">
                                  {draft.file ? draft.file.name : t.auth.uploadSubmission}
                                  <input
                                    type="file"
                                    accept=".pdf,.pptx,.ppsx,.doc,.docx,.zip,.png,.jpg,.jpeg"
                                    hidden
                                    onChange={e => setSubmitDrafts(prev => ({
                                      ...prev,
                                      [hw.id]: { ...draft, file: e.target.files?.[0] || null },
                                    }))}
                                  />
                                </label>
                                <button
                                  type="button"
                                  className="action-btn action-btn-primary"
                                  disabled={homeworkBusy}
                                  onClick={() => handleSubmitHomework(hw.id)}
                                >
                                  {hw.my_submission ? t.auth.resubmitHomework : t.auth.submitHomework}
                                </button>
                              </div>
                              {hw.my_submission?.filename && (
                                <p className="muted-inline">{hw.my_submission.filename}</p>
                              )}
                            </div>
                          )}

                          {isTeacher && expandedHomeworkId === hw.id && (
                            <div className="submission-list">
                              {subs.length === 0 ? (
                                <p className="muted">{t.auth.noHomework}</p>
                              ) : subs.map(sub => (
                                <div key={sub.id} className="submission-row">
                                  <div>
                                    <strong>{sub.student_name}</strong>
                                    {sub.content && <p className="homework-desc">{sub.content}</p>}
                                    <span className="muted-inline">{sub.submitted_at?.slice(0, 16).replace('T', ' ')}</span>
                                  </div>
                                  {sub.has_file && (
                                    <button type="button" className="download-btn" onClick={() => handleDownloadSubmission(sub)}>
                                      {sub.filename || t.download}
                                    </button>
                                  )}
                                </div>
                              ))}
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
