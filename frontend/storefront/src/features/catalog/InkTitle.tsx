import type { CSSProperties } from "react";
import styles from "./InkTitle.module.css";

/**
 * The page's one orchestrated moment: each word rises out of a soft blur while a band of
 * the three process inks (cyan, magenta, yellow) rolls across it in reading direction,
 * then it settles in solid ink. With reduced motion, or on a return visit, it simply
 * appears.
 *
 * The words are plain text in one heading, so crawlers, screen readers and copy-paste see
 * the sentence once, as written.
 */
export function InkTitle({ text, still = false }: { text: string; still?: boolean }) {
  const words = text.split(" ");
  return (
    <h1 className={styles.title} data-still={still}>
      {words.map((word, index) => (
        <span key={index}>
          <span className={styles.word} style={{ "--w": index } as CSSProperties}>
            {word}
          </span>
          {index < words.length - 1 && " "}
        </span>
      ))}
    </h1>
  );
}
