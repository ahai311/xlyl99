import fs from 'node:fs';

/** PNG dimensions are independent of compression ratio and file size. */
export function isPngImage(file, minWidth = 1, minHeight = 1) {
  try {
    const data = fs.readFileSync(file);
    return data.length >= 33
      && data.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))
      && data.toString('ascii', 12, 16) === 'IHDR'
      && data.readUInt32BE(16) >= minWidth && data.readUInt32BE(20) >= minHeight;
  } catch {
    return false;
  }
}
