import logoImg from '../../assets/logo.png'

export default function AppModals({ model }) {
  const { authError, authForm, authLoading, authModal, codeCooldown, handleLogin, handleSelectRole, handleSendCode, handleSignup, isActionPending, roleModalOpen, sendingCode, setAuthForm, setAuthModal, t } = model
  return <>
    {authModal && <div className="auth-overlay" onClick={() => setAuthModal(null)}><div className="auth-modal" onClick={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" aria-label={t.auth.close} onClick={() => setAuthModal(null)}>&times;</button>
      <div className="auth-header"><img src={logoImg} alt="Logo" className="logo-img" /><h2>{authModal === 'login' ? t.auth.loginTitle : t.auth.signupTitle}</h2></div>
      <form className="auth-form" onSubmit={authModal === 'login' ? handleLogin : handleSignup}>
        <div className="form-group"><label>{t.auth.email}</label><input type="email" placeholder="2131445@tongji.edu.cn" value={authForm.email} onChange={(event) => setAuthForm((form) => ({ ...form, email: event.target.value }))} /><small>{t.auth.emailHint}</small></div>
        {authModal === 'signup' && <><div className="form-group code-row"><label>{t.auth.code}</label><div className="code-input-wrap"><input type="text" value={authForm.code} onChange={(event) => setAuthForm((form) => ({ ...form, code: event.target.value }))} /><button type="button" disabled={codeCooldown > 0 || sendingCode} aria-busy={sendingCode} onClick={handleSendCode}>{sendingCode ? t.auth.sendingCode : codeCooldown > 0 ? `${codeCooldown}s` : t.auth.sendCode}</button></div></div><div className="form-group"><label>{t.auth.name}</label><input type="text" value={authForm.name} onChange={(event) => setAuthForm((form) => ({ ...form, name: event.target.value }))} /></div></>}
        <div className="form-group"><label>{t.auth.password}</label><input type="password" value={authForm.password} onChange={(event) => setAuthForm((form) => ({ ...form, password: event.target.value }))} /></div>
        {authModal === 'signup' && <div className="form-group"><label>{t.auth.confirmPassword}</label><input type="password" value={authForm.confirmPassword} onChange={(event) => setAuthForm((form) => ({ ...form, confirmPassword: event.target.value }))} /></div>}
        {authError && <p className="auth-error">{authError}</p>}
        <button type="submit" className="auth-submit" disabled={authLoading} aria-busy={authLoading}>{authLoading ? authModal === 'login' ? t.auth.loggingIn : t.auth.signingUp : authModal === 'login' ? t.auth.loginBtn : t.auth.signupBtn}</button>
      </form>
      <div className="auth-footer">{authModal === 'login' ? <p>{t.auth.noAccount} <button type="button" className="auth-switch-btn" onClick={() => setAuthModal('signup')}>{t.auth.signupBtn}</button></p> : <p>{t.auth.hasAccount} <button type="button" className="auth-switch-btn" onClick={() => setAuthModal('login')}>{t.auth.loginBtn}</button></p>}</div>
    </div></div>}
    {roleModalOpen && <div className="auth-overlay"><div className="auth-modal" role="dialog" aria-modal="true" onClick={(event) => event.stopPropagation()}><div className="auth-header"><img src={logoImg} alt="Logo" className="logo-img" /><h2>{t.auth.roleTitle}</h2></div><div className="role-actions"><button type="button" className="solid-btn" disabled={authLoading} aria-busy={isActionPending('auth:role:student')} onClick={() => handleSelectRole('student')}>{isActionPending('auth:role:student') ? t.auth.processing : t.auth.student}</button><button type="button" className="ghost-btn" disabled={authLoading} aria-busy={isActionPending('auth:role:teacher')} onClick={() => handleSelectRole('teacher')}>{isActionPending('auth:role:teacher') ? t.auth.processing : t.auth.teacher}</button></div>{authError && <p className="auth-error">{authError}</p>}</div></div>}
  </>
}
