const cors = require('cors')
// ruleid: custom_js_cors-wildcard
app.use(cors({ origin: '*' }))
// ruleid: custom_js_cors-wildcard
app.use((req, res) => { res.setHeader('Access-Control-Allow-Origin', '*') })
// ok: custom_js_cors-wildcard
app.use(cors({ origin: 'https://app.example.org' }))
