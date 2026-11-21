/** A labelled text box (or text area) with its error under it. */
export function FieldError({ text }: { text: string | null }) {
  return text ? <small className="field-error">{text}</small> : null;
}

export function TextField({
  label,
  value,
  onChange,
  dir,
  maxLength,
  error = null,
  optional,
  multiline = false,
  placeholder,
  inputMode,
  type = "text",
  hint,
}: {
  label: string;
  value: string;
  onChange: (next: string) => void;
  dir?: "rtl" | "ltr";
  maxLength?: number;
  error?: string | null;
  optional?: string;
  multiline?: boolean;
  placeholder?: string;
  inputMode?: "numeric" | "decimal";
  type?: "text" | "tel" | "url";
  hint?: string;
}) {
  const props = {
    className: "input",
    value,
    dir,
    maxLength,
    placeholder,
    "aria-invalid": !!error,
  };
  return (
    <label className="field">
      <span>
        {label} {optional && <small>({optional})</small>}
      </span>
      {hint && <small className="muted">{hint}</small>}
      {multiline ? (
        <textarea {...props} rows={3} onChange={(event) => onChange(event.target.value)} />
      ) : (
        <input
          {...props}
          type={type}
          inputMode={inputMode}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
      <FieldError text={error} />
    </label>
  );
}
