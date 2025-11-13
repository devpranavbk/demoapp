const fs = require('fs');
const path = require('path');

module.exports = (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  let body = '';
  req.on('data', chunk => {
    body += chunk;
  });
  req.on('end', () => {
    try {
      const { username, password } = JSON.parse(body);
      const credentialsPath = path.join(__dirname, '../data/credentials.json');
      const credentials = JSON.parse(fs.readFileSync(credentialsPath, 'utf8'));
      if (
        username === credentials.username &&
        password === credentials.password
      ) {
        res.status(200).json({ success: true });
      } else {
        res.status(401).json({ success: false, error: 'Invalid credentials' });
      }
    } catch (err) {
      res.status(400).json({ error: 'Invalid request' });
    }
  });
};
