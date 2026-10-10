import type { NextApiRequest, NextApiResponse } from "next";
import fs from "fs";
import path from "path";

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const { id } = req.query;
  if (!id || typeof id !== "string") {
    return res.status(400).json({ error: "Missing document id" });
  }

  // 1. Look in backend/pdf_cache/{id}.pdf
  const pdfCacheDir = path.resolve(process.cwd(), "..", "backend", "pdf_cache");
  const localPdfPath = path.join(pdfCacheDir, `${id}.pdf`);

  if (fs.existsSync(localPdfPath)) {
    const stat = fs.statSync(localPdfPath);
    res.writeHead(200, {
      "Content-Type": "application/pdf",
      "Content-Length": stat.size,
      "Accept-Ranges": "bytes",
      "Access-Control-Allow-Origin": "*",
    });
    const readStream = fs.createReadStream(localPdfPath);
    return readStream.pipe(res);
  }

  // 2. Fallback: proxy from local backend server
  try {
    const backendRes = await fetch(`http://127.0.0.1:8000/api/document/${id}/pdf`);
    if (backendRes.ok) {
      const buffer = await backendRes.arrayBuffer();
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Length", buffer.byteLength);
      res.setHeader("Accept-Ranges", "bytes");
      res.setHeader("Access-Control-Allow-Origin", "*");
      return res.status(200).send(Buffer.from(buffer));
    }
  } catch (e) {
    console.error("Error proxying PDF:", e);
  }

  return res.status(404).json({ error: "PDF not found" });
}
