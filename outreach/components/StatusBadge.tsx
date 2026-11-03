import { STATUS_LABELS, STATUS_STYLES, type ContactStatus } from "@/lib/labels";

export function StatusBadge({ status, large = false }: { status: ContactStatus; large?: boolean }) {
  return (
    <span
      className={`inline-flex rounded-full font-medium ${large ? "px-3 py-1.5 text-sm" : "px-2.5 py-1 text-xs"} ${STATUS_STYLES[status]}`}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
