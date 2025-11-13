import { promises as fs } from 'fs';
import path from 'path';

export default async function handler(req, res) {
  const dbPath = path.join(process.cwd(), 'data', 'items.json');
  try {
    const data = await fs.readFile(dbPath, 'utf8');
    res.status(200).json({ items: JSON.parse(data) });
  } catch (err) {
    res.status(500).json({ error: 'Could not read items.json' });
  }
}
