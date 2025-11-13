export default function handler(req, res) {
  const data = Array.from({ length: 10 }, () => Math.floor(Math.random() * 100) + 1);
  res.status(200).json({ data });
}
