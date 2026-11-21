import { SearchIcon } from "./icons";

/** A search field with its icon; the placeholder is also its accessible name. */
export function SearchBox({
  value,
  onChange,
  placeholder,
  maxLength = 100,
}: {
  value: string;
  onChange: (next: string) => void;
  placeholder: string;
  maxLength?: number;
}) {
  return (
    <label className="search-box">
      <SearchIcon size={20} />
      <input
        className="input"
        type="search"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        maxLength={maxLength}
      />
    </label>
  );
}
