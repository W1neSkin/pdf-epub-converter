import { PDFDocument } from 'pdf-lib';

// Read only PDF properties in the browser. No upload yet.
export async function getPdfInfo(file) {
  const pdf = await PDFDocument.load(await file.arrayBuffer(), {
    ignoreEncryption: true,
    updateMetadata: false,
  });
  return {
    name: file.name,
    title: pdf.getTitle() || '',
    pages: pdf.getPageCount(),
    sizeMb: file.size / (1024 * 1024),
  };
}
