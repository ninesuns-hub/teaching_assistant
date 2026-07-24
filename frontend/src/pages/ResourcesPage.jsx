import { useState } from 'react'
import { RESOURCE_FILTERS } from '../config/uiContent'
import { getMaterialCategory } from '../utils/appUtils'

function ResourceFilters({ activeFilter, setActiveFilter, t }) {
  return (
    <div className="filter-bar" aria-label={t.resourcesTitle}>
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
  )
}

export default function ResourcesPage({ model }) {
  const {
    activeClassId,
    activeFilter,
    classForm,
    classes,
    handleAddStudent,
    handleCreateClass,
    handleDeleteMaterial,
    handleJoinClass,
    handleRemoveStudent,
    handleUploadMaterial,
    isActionPending,
    isStudent,
    isTeacher,
    language,
    materials,
    materialUploadNotice,
    materialSortBy,
    materialSortDirection,
    openMaterialFile,
    secondPageTitle,
    setActiveClassId,
    setActiveFilter,
    setClassForm,
    setMaterialSortBy,
    setMaterialSortDirection,
    setStudentEmailInput,
    setStudentsOpen,
    studentBusy,
    studentEmailInput,
    students,
    studentsOpen,
    t,
    user,
    visibleMaterials,
  } = model
  const [joinOpen, setJoinOpen] = useState(false)

  const submitJoinClass = async () => {
    const joinedClass = await handleJoinClass()
    if (joinedClass) setJoinOpen(false)
  }

  const joinForm = (showCancel = false) => (
    <div className="student-join-form">
      <input
        value={classForm.inviteCode}
        onChange={event => setClassForm(form => ({ ...form, inviteCode: event.target.value }))}
        placeholder={t.auth.inviteCode}
        aria-label={t.auth.inviteCode}
      />
      <button
        type="button"
        className="action-btn action-btn-primary"
        disabled={isActionPending('class:join')}
        aria-busy={isActionPending('class:join')}
        onClick={submitJoinClass}
      >
        {isActionPending('class:join') ? t.auth.processing : t.auth.joinClass}
      </button>
      {showCancel && (
        <button
          type="button"
          className="action-btn action-btn-soft"
          disabled={isActionPending('class:join')}
          onClick={() => setJoinOpen(false)}
        >
          {t.auth.cancelJoin}
        </button>
      )}
    </div>
  )

  return (
    <section id="section-resources" className={`section section-resources ${isTeacher ? 'section-teacher' : 'section-student'}`}>
      <div className="resources-container">
        <div className="resources-header" id={isTeacher ? 'section-classes' : undefined}>
          <h2>{secondPageTitle}</h2>
          {!user && <p className="muted">{t.login}</p>}
        </div>

        {isStudent && user && (
          <section className={`student-class-context ${classes.length === 0 ? 'is-empty' : ''}`} aria-labelledby="student-class-context-title">
            {classes.length > 0 ? (
              <>
                <div className="student-class-context-main">
                  <span className="student-class-kicker">{t.auth.currentClass}</span>
                  <h3 id="student-class-context-title">
                    {classes.find(classroom => classroom.id === activeClassId)?.name || classes[0]?.name}
                  </h3>
                  <p>{t.auth.classResourcesFollowHint}</p>
                </div>
                <div className="student-class-context-actions">
                  <label className="student-class-picker">
                    <span>{t.auth.switchClass}</span>
                    <select value={activeClassId ?? classes[0]?.id ?? ''} onChange={event => setActiveClassId(Number(event.target.value))}>
                      {classes.map(classroom => (
                        <option key={classroom.id} value={classroom.id}>{classroom.name}</option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="action-btn action-btn-primary student-join-toggle"
                    aria-expanded={joinOpen}
                    onClick={() => setJoinOpen(open => !open)}
                  >
                    {t.auth.joinAnotherClass}
                  </button>
                </div>
                {joinOpen && (
                  <div className="student-join-panel">
                    <strong>{t.auth.joinAnotherClass}</strong>
                    <p>{t.auth.studentNoClassHint}</p>
                    {joinForm(true)}
                  </div>
                )}
              </>
            ) : (
              <div className="student-class-context-main">
                <span className="student-class-kicker">{t.auth.currentClass}</span>
                <h3 id="student-class-context-title">{t.auth.joinClass}</h3>
                <p>{t.auth.studentNoClassHint}</p>
                {joinForm()}
              </div>
            )}
          </section>
        )}

        {isTeacher && user && (
          <div className="class-panel teacher-panel">
            <div className="class-actions">
              <input
                value={classForm.name}
                onChange={event => setClassForm(form => ({ ...form, name: event.target.value }))}
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
                  {classes.map(classroom => (
                    <button
                      key={classroom.id}
                      type="button"
                      className={`filter-btn ${activeClassId === classroom.id ? 'active' : ''}`}
                      aria-pressed={activeClassId === classroom.id}
                      disabled={isActionPending('material:upload')}
                      onClick={() => {
                        setActiveClassId(classroom.id)
                        setStudentsOpen(false)
                      }}
                    >
                      {classroom.name}
                    </button>
                  ))}
                </div>
                {activeClassId && (
                  <p className="invite-code-display">
                    {t.auth.inviteCodeLabel}: <strong>{classes.find(classroom => classroom.id === activeClassId)?.invite_code}</strong>
                  </p>
                )}
                {activeClassId && (
                  <div className="student-management-panel">
                    <button
                      type="button"
                      className={`students-fold-toggle ${studentsOpen ? 'open' : ''}`}
                      onClick={() => setStudentsOpen(open => !open)}
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
                            onChange={event => setStudentEmailInput(event.target.value)}
                            placeholder={t.auth.studentEmail}
                          />
                          <button type="button" className="action-btn action-btn-primary" disabled={studentBusy} aria-busy={isActionPending('student:add')} onClick={handleAddStudent}>
                            {isActionPending('student:add') ? t.auth.processing : t.auth.addStudent}
                          </button>
                        </div>
                        {students.length === 0 ? (
                          <p className="muted">{t.auth.noStudents}</p>
                        ) : students.map(student => (
                          <div key={student.id} className="student-row">
                            <div>
                              <strong>{student.name}</strong>
                              <span className="muted-inline">{t.auth.messagesCount}: {student.effective_question_count ?? student.message_count}</span>
                            </div>
                            <button type="button" className="download-btn danger" disabled={studentBusy} aria-busy={isActionPending(`student:remove:${student.id}`)} onClick={() => handleRemoveStudent(student.id)}>
                              {isActionPending(`student:remove:${student.id}`) ? t.auth.deleting : t.auth.removeStudent}
                            </button>
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

        {(isStudent || isTeacher) && user && classes.length > 0 && (
          <>
            <div className="resource-library-header">
              <div>
                <h3>{t.auth.resourceLibrary}</h3>
                {isStudent && <p>{classes.find(classroom => classroom.id === activeClassId)?.name}</p>}
              </div>
              <div className="resource-library-tools">
                <ResourceFilters activeFilter={activeFilter} setActiveFilter={setActiveFilter} t={t} />
                <div className="resource-sort-controls" aria-label={t.auth.materialSort}>
                  <label>
                    <span>{t.auth.sortBy}</span>
                    <select value={materialSortBy} onChange={event => setMaterialSortBy(event.target.value)}>
                      <option value="name">{t.auth.sortByName}</option>
                      <option value="uploadedAt">{t.auth.sortByUploadedAt}</option>
                    </select>
                  </label>
                  <label>
                    <span>{t.auth.sortDirection}</span>
                    <select value={materialSortDirection} onChange={event => setMaterialSortDirection(event.target.value)}>
                      <option value="asc">{t.auth.sortAscending}</option>
                      <option value="desc">{t.auth.sortDescending}</option>
                    </select>
                  </label>
                </div>
                {isTeacher && activeClassId && (
                  <label className="upload-btn upload-btn-primary" aria-busy={isActionPending('material:upload')}>
                    {isActionPending('material:upload') && materialUploadNotice?.filename
                      ? `${t.auth.uploading} ${materialUploadNotice.filename}`
                      : t.auth.uploadMaterial}
                    <input className="visually-hidden-file-input" type="file" accept=".pdf,.pptx,.ppsx" disabled={isActionPending('material:upload')} onChange={handleUploadMaterial} />
                  </label>
                )}
              </div>
            </div>
            {materialUploadNotice?.classId === activeClassId && materialUploadNotice.type !== 'progress' && (
              <div className={`material-upload-notice is-${materialUploadNotice.type}`} role={materialUploadNotice.type === 'error' ? 'alert' : 'status'}>
                {materialUploadNotice.message}
              </div>
            )}
            <div className="resources-grid">
              {visibleMaterials.length === 0 ? (
                <div className="resource-card muted-card">
                  <p className="muted">{materials.length === 0 ? t.auth.noMaterials : (language === 'zh' ? '该分类下暂无资料' : 'No resources in this category')}</p>
                </div>
              ) : visibleMaterials.map(material => (
                <div key={material.id} className="resource-card">
                  <div className="card-type">{t.filters[getMaterialCategory(material)]}</div>
                  <h3>{material.filename}</h3>
                  <p>{(material.file_size / 1024 / 1024).toFixed(2)} MB</p>
                  <div className="card-footer">
                    <span>{material.uploaded_at?.slice(0, 10)}</span>
                    <div className="card-actions">
                      <button type="button" className="download-btn" disabled={isActionPending(`material:view:${material.id}`)} aria-busy={isActionPending(`material:view:${material.id}`)} onClick={() => openMaterialFile(material, false)}>
                        {isActionPending(`material:view:${material.id}`) ? t.auth.opening : t.view}
                      </button>
                      <button type="button" className="download-btn" disabled={isActionPending(`material:download:${material.id}`)} aria-busy={isActionPending(`material:download:${material.id}`)} onClick={() => openMaterialFile(material, true)}>
                        {isActionPending(`material:download:${material.id}`) ? t.auth.downloading : t.download}
                      </button>
                      {isTeacher && (
                        <button
                          type="button"
                          className="download-btn danger"
                          disabled={isActionPending(`material:delete:${material.id}`)}
                          aria-busy={isActionPending(`material:delete:${material.id}`)}
                          onClick={() => handleDeleteMaterial(material)}
                        >
                          {isActionPending(`material:delete:${material.id}`) ? t.auth.deleting : t.auth.deleteMaterial}
                        </button>
                      )}
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
