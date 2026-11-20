import { AnimatePresence, m, useDragControls } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { CloseIcon } from "./icons";
import styles from "./BottomSheet.module.css";

/**
 * A sheet that slides up from the bottom on phones. Drag its handle or title down, or
 * tap outside, to close. The drag starts only there, so the list inside scrolls freely.
 */
export function BottomSheet({
  open,
  onClose,
  title,
  closeLabel,
  footer,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  closeLabel: string;
  footer?: ReactNode;
  children: ReactNode;
}) {
  const panel = useRef<HTMLDivElement>(null);
  const drag = useDragControls();

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    panel.current?.focus({ preventScroll: true });
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onClose]);

  return createPortal(
    <AnimatePresence>
      {open && (
        <div className={styles.root}>
          <m.div
            className={styles.backdrop}
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <m.div
            ref={panel}
            role="dialog"
            aria-modal="true"
            aria-label={title}
            tabIndex={-1}
            className={styles.sheet}
            initial={{ y: "100%" }}
            animate={{ y: 0 }}
            exit={{ y: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
            drag="y"
            dragControls={drag}
            dragListener={false}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.6 }}
            onDragEnd={(_, info) => {
              if (info.offset.y > 120 || info.velocity.y > 600) onClose();
            }}
          >
            <div className={styles.grip} onPointerDown={(e) => drag.start(e)}>
              <div className={styles.handle} aria-hidden="true" />
              <div className={styles.head}>
                <h2>{title}</h2>
                <button
                  type="button"
                  className="icon-btn"
                  onClick={onClose}
                  onPointerDown={(e) => e.stopPropagation()}
                  aria-label={closeLabel}
                >
                  <CloseIcon />
                </button>
              </div>
            </div>
            <div className={styles.body}>{children}</div>
            {footer && <div className={styles.footer}>{footer}</div>}
          </m.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  );
}
