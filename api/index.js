import { promises as fs } from 'fs';
import path from 'path';

export default async function handler(req, res) {
  res.status(200).json({ message: 'Welcome to the simple API (Vercel Serverless)!' });
}
