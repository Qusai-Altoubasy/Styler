import type { CSSProperties } from "react";
import type { BrandColor } from "@styler/shared/api/types";
import { inkVar } from "@styler/shared/theme/ink";
import styles from "./PrintImage.module.css";

/**
 * A product or category image framed with a printer's crop marks. Without an image it
 * shows a halftone dot pattern in the given ink instead of an empty box.
 */
export function PrintImage({
  src,
  alt,
  ink,
  marks = true,
  eager = false,
}: {
  src: string | null;
  alt: string;
  ink: BrandColor;
  marks?: boolean;
  eager?: boolean;
}) {
  return (
    <div className={styles.frame} style={{ "--ink": inkVar(ink) } as CSSProperties}>
      {src ? (
        <img
          className={styles.img}
          src={src}
          alt={alt}
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onLoad={(e) => e.currentTarget.classList.add(styles.loaded ?? "")}
        />
      ) : (
        <div className={styles.halftone} role="img" aria-label={alt} />
      )}
      {marks && <span className={styles.marks} aria-hidden="true" />}
    </div>
  );
}
