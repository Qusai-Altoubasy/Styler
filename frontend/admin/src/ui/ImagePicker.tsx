import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useErrorText } from "../lib/errors";
import { uploadImage } from "../lib/upload";
import { ImageIcon } from "./icons";

/** The image of a category or product: its key to save, and a link to show it. */
export interface ImageValue {
  key: string | null;
  url: string | null;
}

/**
 * Picks a photo from the phone, shrinks it to WebP and uploads it right away, so saving
 * the form only sends the key. The preview is the local file: a fresh upload is not
 * served until the form is saved and the server moves it out of `tmp/`.
 */
export function ImagePicker({
  value,
  onChange,
  onBusyChange,
}: {
  value: ImageValue;
  onChange: (next: ImageValue) => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const { t } = useTranslation();
  const errorText = useErrorText();
  const input = useRef<HTMLInputElement>(null);
  const localUrl = useRef<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (localUrl.current) URL.revokeObjectURL(localUrl.current);
    },
    [],
  );

  const setPreview = (url: string | null) => {
    if (localUrl.current) URL.revokeObjectURL(localUrl.current);
    localUrl.current = url;
  };

  const pick = async (file: File) => {
    setError(null);
    setBusy(true);
    onBusyChange(true);
    try {
      const { key, image } = await uploadImage(file);
      const url = URL.createObjectURL(image);
      setPreview(url);
      onChange({ key, url });
    } catch (caught) {
      setError(errorText(caught));
    } finally {
      setBusy(false);
      onBusyChange(false);
    }
  };

  return (
    <div className="image-picker">
      <div className="image-picker-frame" aria-busy={busy}>
        {value.url ? <img src={value.url} alt="" /> : <ImageIcon size={34} className="muted" />}
        {busy && (
          <span className="image-picker-busy">
            <span className="spinner" aria-hidden="true" />
            {t("imageUploading")}
          </span>
        )}
      </div>
      <div className="image-picker-actions">
        <button
          type="button"
          className="btn btn-sm"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          {value.url ? t("imageChange") : t("imagePick")}
        </button>
        {value.url && (
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            disabled={busy}
            onClick={() => {
              setPreview(null);
              onChange({ key: null, url: null });
            }}
          >
            {t("imageRemove")}
          </button>
        )}
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      <input
        ref={input}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = ""; // the same photo can be picked again after an error
          if (file) void pick(file);
        }}
      />
    </div>
  );
}
