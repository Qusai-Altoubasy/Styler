/** The longest side of a saved image: sharp on a phone, small to store and load. */
export const MAX_SIDE = 1600;
const QUALITIES = [0.85, 0.72, 0.6];

/** The size that fits inside max×max, keeping the shape; never enlarges. */
export function fitWithin(width: number, height: number, max: number) {
  const scale = Math.min(1, max / Math.max(width, height));
  return {
    width: Math.max(1, Math.round(width * scale)),
    height: Math.max(1, Math.round(height * scale)),
  };
}

export class ImageReadError extends Error {
  constructor() {
    super("image_unreadable");
    this.name = "ImageReadError";
  }
}

/** Still over the upload limit at the smallest size and lowest quality. */
export class ImageTooLargeError extends Error {
  constructor() {
    super("image_too_large");
    this.name = "ImageTooLargeError";
  }
}

/** A decoded photo, whichever way the browser could read it. */
interface Decoded {
  source: CanvasImageSource;
  width: number;
  height: number;
  close: () => void;
}

/**
 * Resizes a picked photo and converts it to WebP under `maxBytes`, all in the browser:
 * the server does no image processing. The phone's rotation (EXIF) is applied. If it is
 * still too large, the quality drops, then the size.
 */
export async function toWebp(file: Blob, maxBytes: number): Promise<Blob> {
  const image = await decode(file);
  try {
    for (let side = MAX_SIDE; side >= 400; side = Math.round(side * 0.75)) {
      const canvas = draw(image, side);
      for (const quality of QUALITIES) {
        const blob = await encodeWebp(canvas, quality);
        if (blob.size <= maxBytes) return blob;
      }
    }
  } finally {
    image.close();
  }
  throw new ImageTooLargeError();
}

/**
 * createImageBitmap first (the phone's rotation applied). Some browsers refuse its
 * options or some formats there, so it is tried without options, then through an <img>,
 * which applies the rotation by itself and reads whatever the browser can show.
 */
async function decode(file: Blob): Promise<Decoded> {
  for (const options of [{ imageOrientation: "from-image" } as const, undefined]) {
    try {
      const bitmap = await createImageBitmap(file, options);
      return {
        source: bitmap,
        width: bitmap.width,
        height: bitmap.height,
        close: () => bitmap.close(),
      };
    } catch {
      // try the next way
    }
  }
  const url = URL.createObjectURL(file);
  const img = new Image();
  img.src = url;
  try {
    await img.decode();
  } catch {
    URL.revokeObjectURL(url);
    throw new ImageReadError();
  }
  return {
    source: img,
    width: img.naturalWidth,
    height: img.naturalHeight,
    close: () => URL.revokeObjectURL(url),
  };
}

function draw(image: Decoded, side: number): HTMLCanvasElement {
  const { width, height } = fitWithin(image.width, image.height, side);
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new ImageReadError();
  context.imageSmoothingQuality = "high";
  context.drawImage(image.source, 0, 0, width, height);
  return canvas;
}

/**
 * The browser's own encoder when it has one. Safari has none and silently returns a PNG,
 * so the type is checked and the WebAssembly encoder is loaded on demand instead.
 */
async function encodeWebp(canvas: HTMLCanvasElement, quality: number): Promise<Blob> {
  const native = await new Promise<Blob | null>((done) =>
    canvas.toBlob(done, "image/webp", quality),
  );
  if (native?.type === "image/webp") return native;
  const context = canvas.getContext("2d");
  if (!context) throw new ImageReadError();
  const { default: encode } = await import("@jsquash/webp/encode.js");
  const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
  const buffer = await encode(pixels, { quality: Math.round(quality * 100) });
  return new Blob([buffer], { type: "image/webp" });
}
