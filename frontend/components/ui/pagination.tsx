import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
  label: string;
}

export function Pagination({ page, pageSize, total, onPageChange, label }: PaginationProps) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <nav aria-label={label} className="mt-4 flex items-center justify-between gap-3">
      <Button variant="secondary" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
        <ChevronLeft aria-hidden="true" />
        Previous
      </Button>
      <span className="text-sm text-slate tabular">
        Page {page} of {pages}
      </span>
      <Button variant="secondary" onClick={() => onPageChange(page + 1)} disabled={page >= pages}>
        Next
        <ChevronRight aria-hidden="true" />
      </Button>
    </nav>
  );
}
