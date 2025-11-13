export default function handler(req, res) {
  setTimeout(() => {
    res.status(200).json({ result: Array.from({ length: 1000 }, (_, i) => i).reduce((a, b) => a + b, 0) });
  }, 200);
}
