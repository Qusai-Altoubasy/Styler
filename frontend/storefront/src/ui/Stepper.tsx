import { useState } from "react";
import { digitsOnly } from "@styler/shared/utils/digits";
import { MinusIcon, PlusIcon } from "./icons";
import styles from "./Stepper.module.css";

/** A number input with − and + buttons, clamped between min and max. */
export function Stepper({
  value,
  onChange,
  min = 1,
  max,
  label,
  decreaseLabel,
  increaseLabel,
  size = "md",
}: {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max: number;
  label: string;
  decreaseLabel: string;
  increaseLabel: string;
  size?: "sm" | "md";
}) {
  const [draft, setDraft] = useState(String(value));
  // Follow outside changes (another tab, the cart) without an effect.
  const [shown, setShown] = useState(value);
  if (shown !== value) {
    setShown(value);
    setDraft(String(value));
  }

  const commit = (raw: string) => {
    const n = Math.min(max, Math.max(min, Math.round(Number(raw)) || min));
    setDraft(String(n));
    if (n !== value) onChange(n);
  };

  return (
    <div className={styles.stepper} data-size={size}>
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        aria-label={decreaseLabel}
      >
        <MinusIcon size={18} />
      </button>
      <input
        inputMode="numeric"
        dir="ltr"
        aria-label={label}
        value={draft}
        onChange={(e) => setDraft(digitsOnly(e.target.value).slice(0, 6))}
        onBlur={(e) => commit(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && commit(e.currentTarget.value)}
      />
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        aria-label={increaseLabel}
      >
        <PlusIcon size={18} />
      </button>
    </div>
  );
}
