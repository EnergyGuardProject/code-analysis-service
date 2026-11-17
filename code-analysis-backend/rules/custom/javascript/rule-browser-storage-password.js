function login(username, password, accessToken) {
  // ruleid: custom_js_browser-storage-password
  localStorage.setItem('user', JSON.stringify({username, password, accessToken}))
  // ruleid: custom_js_browser-storage-password
  localStorage.setItem('creds', JSON.stringify({ user: username, pass: credentials.password }))
  // ruleid: custom_js_browser-storage-password
  sessionStorage.setItem('pw', password)
  // ok: custom_js_browser-storage-password
  localStorage.setItem('user', JSON.stringify({username}))
  // ok: custom_js_browser-storage-password
  localStorage.setItem('theme', 'dark')
}
