import styles from "./RegistrationTitle.module.css";

/**
 * The page's one orchestrated moment: the heading prints like a press run. Cyan,
 * magenta and yellow plates land out of register, slide into place, then the black
 * plate prints on top. With reduced motion it simply appears registered.
 *
 * The plates are empty elements that draw the text from `data-text` in CSS, so the
 * heading's text exists once: crawlers, link previews and copy-paste see it once.
 */
export function RegistrationTitle({ text, still = false }: { text: string; still?: boolean }) {
  return (
    <h1 className={styles.title} data-still={still}>
      <span className={`${styles.plate} ${styles.cyan}`} data-text={text} aria-hidden="true" />
      <span className={`${styles.plate} ${styles.magenta}`} data-text={text} aria-hidden="true" />
      <span className={`${styles.plate} ${styles.yellow}`} data-text={text} aria-hidden="true" />
      <span className={styles.key}>{text}</span>
    </h1>
  );
}
