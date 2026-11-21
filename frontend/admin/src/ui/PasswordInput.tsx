import { useState } from "react";
import { EyeIcon, EyeOffIcon } from "./icons";

/** A password box with a show/hide button: easier to type right on a phone. */
export function PasswordInput({
  value,
  onChange,
  autoComplete,
  autoFocus = false,
  invalid = false,
  showLabel,
  hideLabel,
}: {
  value: string;
  onChange: (next: string) => void;
  autoComplete: "current-password" | "new-password";
  autoFocus?: boolean;
  invalid?: boolean;
  showLabel: string;
  hideLabel: string;
}) {
  const [visible, setVisible] = useState(false);
  // LTR as a whole, so the eye button sits at the end of what is typed in both languages.
  return (
    <span className="password-input" dir="ltr">
      <input
        className="input"
        type={visible ? "text" : "password"}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete={autoComplete}
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        autoFocus={autoFocus}
        aria-invalid={invalid}
        maxLength={128}
      />
      <button
        type="button"
        className="icon-btn"
        onClick={() => setVisible((shown) => !shown)}
        aria-label={visible ? hideLabel : showLabel}
        aria-pressed={visible}
      >
        {visible ? <EyeOffIcon size={20} /> : <EyeIcon size={20} />}
      </button>
    </span>
  );
}
