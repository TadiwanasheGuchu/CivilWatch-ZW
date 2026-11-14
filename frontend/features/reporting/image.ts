/**
 * Shrink photos on the phone before upload: a 4 MB camera photo becomes a
 * few hundred KB, which matters on metered mobile data. The server still
 * validates and re-encodes every photo; this is only about bandwidth.
 */
export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;
const MAX_DIMENSION = 1600;
const QUALITY = 0.8;

export class PhotoPreparationError extends Error {}

async function toJpeg(bitmap: ImageBitmap): Promise<Blob | null> {
  const scale = Math.min(1, MAX_DIMENSION / Math.max(bitmap.width, bitmap.height));
  const width = Math.round(bitmap.width * scale);
  const height = Math.round(bitmap.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.drawImage(bitmap, 0, 0, width, height);
  return new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", QUALITY));
}

export async function preparePhoto(file: File): Promise<Blob> {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    throw new PhotoPreparationError("Choose a JPEG, PNG or WebP photo.");
  }
  try {
    if (typeof createImageBitmap === "function") {
      // Apply the camera's rotation so the preview and upload are upright.
      const bitmap = await createImageBitmap(file, { imageOrientation: "from-image" });
      const blob = await toJpeg(bitmap);
      bitmap.close();
      if (blob && blob.size > 0) return blob;
    }
  } catch {
    // Older browsers: fall through and send the original.
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    throw new PhotoPreparationError("This photo is larger than 10 MB. Choose a smaller photo.");
  }
  return file;
}
