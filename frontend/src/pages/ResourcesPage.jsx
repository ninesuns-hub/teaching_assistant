import { RESOURCE_FILTERS } from '../config/uiContent'
import { getMaterialCategory } from '../utils/appUtils'

export default function ResourcesPage({ model }) {
  const { activeClassId, activeFilter, classForm, classes, generatingLearning, handleAddStudent, handleCreateClass, handleGenerateClassFeedback, handleGenerateMyReport, handleGenerateStudentReport, handleJoinClass, handleRemoveStudent, handleUploadMaterial, handleViewStudentReport, isActionPending, isStudent, isTeacher, language, materials, openMaterialFile, secondPageTitle, setActiveClassId, setActiveFilter, setClassForm, setStudentEmailInput, setStudentsOpen, studentBusy, studentEmailInput, students, studentsOpen, t, user, visibleMaterials } = model

  return (
    <section id="section-resources" className={`section section-resources ${isTeacher ? 'section-teacher' : 'section-student'}`}>
          <div className="resources-container">
            <div className="resources-header" id={isTeacher ? 'section-classes' : undefined}>
              <h2>{secondPageTitle}</h2>
              {!isTeacher && user && classes.length > 0 && (
                <div className="filter-bar">
                  {RESOURCE_FILTERS.map(filter => (
                    <button
                      key={filter}
                      type="button"
                      className={`filter-btn ${activeFilter === filter ? 'active' : ''}`}
                      aria-pressed={activeFilter === filter}
                      onClick={() => setActiveFilter(filter)}
                    >
                      {t.filters[filter]}
                    </button>
                  ))}
                </div>
              )}
              {!user && <p className="muted">{t.login}</p>}
            </div>

            {isTeacher && user && (
              <div className="class-panel teacher-panel">
                <div className="class-actions">
                  <input
                    value={classForm.name}
                    onChange={e => setClassForm(p => ({ ...p, name: e.target.value }))}
                    placeholder={t.auth.className}
                  />
                  <button type="button" className="action-btn action-btn-primary" disabled={isActionPending('class:create')} aria-busy={isActionPending('class:create')} onClick={handleCreateClass}>
                    {isActionPending('class:create') ? t.auth.processing : t.auth.createClass}
                  </button>
                </div>
                {classes.length === 0 ? (
                  <p className="muted">{t.auth.teacherNoClassHint}</p>
                ) : (
                  <>
                    <div className="class-tabs">
                      {classes.map(c => (
                        <button
                          key={c.id}
                          type="button"
                          className={`filter-btn ${activeClassId === c.id ? 'active' : ''}`}
                          aria-pressed={activeClassId === c.id}
                          onClick={() => {
                            setActiveClassId(c.id)
                            setStudentsOpen(false)
                          }}
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                    {activeClassId && (
                      <p className="invite-code-display">
                        {t.auth.inviteCodeLabel}: <strong>{classes.find(c => c.id === activeClassId)?.invite_code}</strong>
                      </p>
                    )}
                    {activeClassId && (
                      <label className="upload-btn" aria-busy={isActionPending('material:upload')}>
                        {isActionPending('material:upload') ? t.auth.uploading : t.auth.uploadMaterial}
                        <input className="visually-hidden-file-input" type="file" accept=".pdf,.pptx,.ppsx" disabled={isActionPending('material:upload')} onChange={handleUploadMaterial} />
                      </label>
                    )}
                    {activeClassId && (
                      <div className="learning-panel">
                        <h3>{t.auth.learningTitle}</h3>
                        <div className="learning-actions">
                          <button
                            type="button"
                            className="solid-btn"
                            disabled={generatingLearning}
                            aria-busy={isActionPending('learning:class')}
                            onClick={handleGenerateClassFeedback}
                          >
                            {isActionPending('learning:class') ? t.auth.generating : t.auth.generateClassFeedback}
                          </button>
                        </div>
                        <button
                          type="button"
                          className={`students-fold-toggle ${studentsOpen ? 'open' : ''}`}
                          onClick={() => setStudentsOpen(o => !o)}
                          aria-expanded={studentsOpen}
                        >
                          <span className="students-fold-label">
                            {t.auth.classStudents}
                            <span className="students-fold-count">{students.length}</span>
                          </span>
                          <span className="students-fold-meta">
                            {studentsOpen ? t.auth.collapseStudents : t.auth.expandStudents}
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                              <path d="M6 9l6 6 6-6" />
                            </svg>
                          </span>
                        </button>
                        {studentsOpen && (
                          <div className="student-list students-fold-body">
                            <div className="student-manage-row">
                              <input
                                value={studentEmailInput}
                                onChange={(e) => setStudentEmailInput(e.target.value)}
                                placeholder={t.auth.studentEmail}
                              />
                              <button type="button" className="action-btn action-btn-primary" disabled={studentBusy} aria-busy={isActionPending('student:add')} onClick={handleAddStudent}>
                                {isActionPending('student:add') ? t.auth.processing : t.auth.addStudent}
                              </button>
                            </div>
                            {students.length === 0 ? (
                              <p className="muted">{t.auth.noStudents}</p>
                            ) : students.map(s => (
                              <div key={s.id} className="student-row">
                                <div>
                                  <strong>{s.name}</strong>
                                  <span className="muted-inline">{t.auth.messagesCount}: {s.effective_question_count ?? s.message_count}</span>
                                </div>
                                <div className="card-actions">
                                  <button type="button" className="download-btn" disabled={isActionPending(`learning:view:${s.id}`)} aria-busy={isActionPending(`learning:view:${s.id}`)} onClick={() => handleViewStudentReport(s.id)}>
                                    {isActionPending(`learning:view:${s.id}`) ? t.auth.loading : t.auth.viewReport}
                                  </button>
                                  <button
                                    type="button"
                                    className="download-btn"
                                    disabled={generatingLearning}
                                    aria-busy={isActionPending(`learning:student:${s.id}`)}
                                    onClick={() => handleGenerateStudentReport(s.id)}
                                  >
                                    {isActionPending(`learning:student:${s.id}`) ? t.auth.generating : t.auth.generateReport}
                                  </button>
                                  <button type="button" className="download-btn danger" disabled={studentBusy} aria-busy={isActionPending(`student:remove:${s.id}`)} onClick={() => handleRemoveStudent(s.id)}>
                                    {isActionPending(`student:remove:${s.id}`) ? t.auth.deleting : t.auth.removeStudent}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {isStudent && user && (
              <div className="class-panel student-panel">
                {classes.length === 0 ? (
                  <>
                    <p className="muted">{t.auth.studentNoClassHint}</p>
                    <div className="class-actions">
                      <input
                        value={classForm.inviteCode}
                        onChange={e => setClassForm(p => ({ ...p, inviteCode: e.target.value }))}
                        placeholder={t.auth.inviteCode}
                      />
                      <button type="button" className="action-btn action-btn-primary" disabled={isActionPending('class:join')} aria-busy={isActionPending('class:join')} onClick={handleJoinClass}>
                        {isActionPending('class:join') ? t.auth.processing : t.auth.joinClass}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p className="muted">{t.auth.selectClassHint}</p>
                    <div className="class-tabs">
                      {classes.map(c => (
                        <button
                          key={c.id}
                          type="button"
                          className={`filter-btn ${activeClassId === c.id ? 'active' : ''}`}
                          aria-pressed={activeClassId === c.id}
                          onClick={() => setActiveClassId(c.id)}
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                    <div className="class-actions join-more">
                      <input
                        value={classForm.inviteCode}
                        onChange={e => setClassForm(p => ({ ...p, inviteCode: e.target.value }))}
                        placeholder={t.auth.inviteCode}
                      />
                      <button type="button" className="action-btn action-btn-soft" disabled={isActionPending('class:join')} aria-busy={isActionPending('class:join')} onClick={handleJoinClass}>
                        {isActionPending('class:join') ? t.auth.processing : t.auth.joinClass}
                      </button>
                    </div>
                    {activeClassId && (
                      <div className="learning-panel">
                        <button
                          type="button"
                          className="solid-btn"
                          disabled={generatingLearning}
                          aria-busy={isActionPending('learning:self')}
                          onClick={handleGenerateMyReport}
                        >
                          {isActionPending('learning:self') ? t.auth.generating : t.auth.generateMyReport}
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {(isStudent || isTeacher) && user && classes.length > 0 && (
              <>
                {isTeacher && (
                  <div className="resource-library-header">
                    <h3>{t.resourcesTitle}</h3>
                    <div className="filter-bar">
                      {RESOURCE_FILTERS.map(filter => (
                        <button
                          key={filter}
                          type="button"
                          className={`filter-btn ${activeFilter === filter ? 'active' : ''}`}
                          aria-pressed={activeFilter === filter}
                          onClick={() => setActiveFilter(filter)}
                        >
                          {t.filters[filter]}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              <div className="resources-grid">
                {visibleMaterials.length === 0 ? (
                  <div className="resource-card muted-card">
                    <p className="muted">{materials.length === 0 ? t.auth.noClasses : (language === 'zh' ? '该分类下暂无资料' : 'No resources in this category')}</p>
                  </div>
                ) : visibleMaterials.map(m => (
                  <div key={m.id} className="resource-card">
                    <div className="card-type">{t.filters[getMaterialCategory(m)]}</div>
                    <h3>{m.filename}</h3>
                    <p>{(m.file_size / 1024 / 1024).toFixed(2)} MB</p>
                    <div className="card-footer">
                      <span>{m.uploaded_at?.slice(0, 10)}</span>
                      <div className="card-actions">
                        <button type="button" className="download-btn" disabled={isActionPending(`material:view:${m.id}`)} aria-busy={isActionPending(`material:view:${m.id}`)} onClick={() => openMaterialFile(m, false)}>
                          {isActionPending(`material:view:${m.id}`) ? t.auth.opening : t.view}
                        </button>
                        <button type="button" className="download-btn" disabled={isActionPending(`material:download:${m.id}`)} aria-busy={isActionPending(`material:download:${m.id}`)} onClick={() => openMaterialFile(m, true)}>
                          {isActionPending(`material:download:${m.id}`) ? t.auth.downloading : t.download}
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              </>
            )}
          </div>
        </section>
  )
}
