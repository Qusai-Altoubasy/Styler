import { api, unwrap } from "@styler/shared/api/client";
import { toWebp } from "./image";

export class UploadError extends Error {
  constructor() {
    super("upload_failed");
    this.name = "UploadError";
  }
}

/**
 * Uploads a picked photo straight to the bucket and returns its `tmp/` key, which the
 * category or product form then saves. The API only signs the upload (presigned POST):
 * the image never passes through the server.
 */
export async function uploadImage(file: File): Promise<{ key: string; image: Blob }> {
  const target = unwrap(
    await api.POST("/api/admin/media/upload-url", { body: { content_type: "image/webp" } }),
  );
  const image = await toWebp(file, target.max_bytes);
  const form = new FormData();
  for (const [name, value] of Object.entries(target.fields)) form.append(name, value);
  form.append("file", image, "image.webp"); // last: S3 ignores fields after the file
  let response: Response;
  try {
    response = await fetch(target.url, { method: "POST", body: form });
  } catch {
    throw new UploadError();
  }
  if (!response.ok) throw new UploadError();
  return { key: target.key, image };
}
