function save(accessToken, theme) {
  // ruleid: custom_js_browser-storage-token
  localStorage.setItem('token', accessToken)
  // ruleid: custom_js_browser-storage-token
  localStorage.setItem('user', JSON.stringify({name: 'x', accessToken}))
  // ok: custom_js_browser-storage-token
  localStorage.setItem('theme', theme)
}
