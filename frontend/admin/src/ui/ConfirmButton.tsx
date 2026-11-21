import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { TrashIcon } from "./icons";

/**
 * Every delete needs a second tap: the first turns the button red and asks again, and it
 * goes back to normal after a few seconds if the second tap never comes.
 */
export function ConfirmButton({
  onConfirm,
  pending = false,
  children,
  className = "",
}: {
  onConfirm: () => void;
  pending?: boolean;
  children?: ReactNode;
  className?: string;
}) {
  const { t } = useTranslation();
  const [armed, setArmed] = useState(false);

  useEffect(() => {
    if (!armed) return;
    const timer = window.setTimeout(() => setArmed(false), 5000);
    return () => window.clearTimeout(timer);
  }, [armed]);

  return (
    <button
      type="button"
      className={`btn btn-danger ${armed ? "is-armed" : ""} ${className}`}
      disabled={pending}
      aria-live="polite"
      onClick={() => {
        if (!armed) return setArmed(true);
        setArmed(false);
        onConfirm();
      }}
    >
      <TrashIcon size={18} />
      {pending ? t("deleting") : armed ? t("confirmDelete") : (children ?? t("delete"))}
    </button>
  );
}
